# TRANSPLANT — the faithful source-level summon transplant (final synthesis)

**The round's question, verbatim from the user:** *"faithfully transplant our OWN models into these [summon]
animations — and maybe at some point export them into Blender."* The prior "puppet overlay" approach (hide the
native creature, composite a rigid FBX whose per-frame world transform we hand-choreograph) is a FIDELITY DEAD
END — proven over 10 FLIGHT iterations. A rigid billboard cannot read as a creature flying-down / banking /
shrinking / rolling. This document synthesizes the T1–T4 / D1–D4 phase slices into the answer, the pipeline,
the Blender round-trip, the risks, and the provenance ledger.

Confidence tags throughout: **PROVEN** (statically or independently verified in a phase slice, or byte-validated
on real bytes), **PLAUSIBLE** (source-traced / one-step-inferred, not yet run in-game), **SPECULATIVE**
(reasoned, unverified). Native RVAs are image-base-relative to the user's own installed
`FF9SpecialEffectPlugin.dll` (x64 `ImageBase 0x180000000`). C# cites are relative to
`C:/gd/FFIX/Memoria/Assembly-CSharp/`; kit cites relative to `ff9mapkit/ff9mapkit/`.

---

## 1. THE ANSWER — a faithful transplant is REAL, and the winning path is the HYBRID

**YES. A faithful source-level transplant is feasible, and the recommended path is the HYBRID** (T1 option
2.a, ratified by D1): **our own skinned model, posed EACH FRAME by the dragon's real 93 world-matrices read
live from `*(SummonData+0x38)`, rendered through Unity's `Camera.main` which the plugin stamps with the native
per-frame camera.** This is the transplant the overlay could never be — *our mesh + the dragon's actual
articulation + its actual root flight + its authored 0.02→3.0 scale sweep + its native camera (15 hard cuts,
47°→24° push-in)* — every term the hand-choreographed billboard failed to fake, all inherited, all in
perfect lockstep, all provenance-clean (zero stock bytes shipped).

### 1.1 The finding that decides the design — camera inheritance does NOT require the native slot (PROVEN)

The brief's explicit contingency was: *"if only the native slot gets the true camera, say so and make that the
target."* **It does not.** The decisive result (T4 §1.2, D1 §0, re-derived independently in D1-VERIFY and
V-C1, both CONFIRMED):

- During any summon, `Camera.main.worldToCameraMatrix` **and** `.projectionMatrix` are stamped **every frame**
  from the plugin's real camera — `SFX.UpdateCamera()` copies 13 floats out of the DLL's installed camera via
  a real P/Invoke (`SFX.cs:1590-1605`; `SFX_UpdateCamera` native body RVA `0x211df0`), driven unconditionally
  each battle-loop tick (`battle.cs:86` → `SFXDataCamera.UpdateCamera()` when `currentCameraEngine==SFX_PLUGIN`,
  set in `SFXDataMesh.Runtime.Begin()` `SFXDataMesh.cs:607`). **A normal Unity object rendered during the cast
  is projected through that same stamped camera — for free, through every cut and zoom.**
- The managed `PsxProj2UnityProj` reconstruction reproduces the native GTE principal point **by construction on
  the vertical axis**: `PsxScreenHeightNative=220` → `bottom=220/2.2=100`, `top=120` = native `OFY=120`
  (`PsxCamera.cs:172-178`, `FieldMap.cs:2336`). **Honest scope (per D1-VERIFY):** vertical pixel-equality is
  proven-by-construction; the **horizontal** principal point is widescreen-aspect-dependent
  (`FieldMap.CalcPsxScreenWidth = PsxScreenHeightNative·Screen.width/Screen.height`), so full horizontal
  pixel-equality is **measured at Milestone 0**, not free. The recommendation is unaffected — we hide the
  native body and show only our puppet, so we need our puppet merely at the creature's world point in
  `Camera.main`'s frame, not pixel-registered onto the native GTE output.

**Consequence:** the native slot (T2) is **not required** for fidelity of *motion* or *camera* — the two things
the overlay got wrong. The **only** thing the native slot buys over the hybrid is **per-poly depth interleave
between our mesh and the screen-space effect prims** (T4 §1.5) — and that matters only for effects that
physically *wrap* the creature body, and is **measurable offline before any playtest.**

### 1.2 The three candidate paths, and why the hybrid wins on all three axes

| axis the overlay failed | **HYBRID** (live `+0x38` bone drive, T1 §2.a) | **T2 native slot** (model-image swap) | **T1b baked-clip FileList** |
|---|---|---|---|
| **articulation** (wing-flap, body-flex) | **FAITHFUL** — driven by `+0x38` (PROVEN read path) | EXACT — native motion clip | **NONE inherited** — only the FBX's own idle |
| **root flight** (~40–73k-unit fly-by) | **FAITHFUL** — folded into the same read | EXACT | ⚠ needs a separate runtime `+0x40` feed |
| **scale sweep** (0.02→3.0×) | **FAITHFUL** — inside the `+0x38` columns | EXACT | ⚠ same runtime feed |
| **camera** (15 cuts, 47°→24° zoom) | **FAITHFUL** — `Camera.main`==native (§1.1) | EXACT — GTE draws it | **FAITHFUL** — same mechanism |
| **clock / WAIT-hold sync** | UNIFIED — sampled on the native tick | EXACT — welded to tick | UNIFIED on `SFX.frameIndex` |
| **effect DEPTH interleave** | **BROKEN** — screen-space vs perspective, wholesale sort | **EXACT** — shared ordering table | BROKEN — same regime split |
| **effort** | **MED** (one managed feature) | HIGH (behind untested $0 W0 gate) | LOW (existing path, but under-captures) |
| **provenance** | cleanest — reads pose to drive our mesh, ships no stock bytes | verbatim-fork class (build-time transform of the user's install) | clean, but the baked clip is stock content → SCRATCH-only |

**Reading:** the hybrid **closes every column the overlay failed** and its *only* residual is the effect-depth
regime — a wholesale front/behind sort of our perspective mesh against the plugin's screen-space effect prims
(`SFXRender.Render()` forces `worldToCameraMatrix=identity` for the effect prims, `SFXRender.cs:130`; a real
Unity FBX does not share that Z axis, T4 §1.5). For a plunge-camera summon whose bursts frame the creature
fore/background this reads acceptably; for effects that pass *through* the body volume it will not. **Native
(T2) is the only path that removes it — and that is the entire fidelity delta between hybrid and native.**

**T1b (baked-clip FileList) is NOT the delivery vehicle** even though it reuses the proven rung-7 route,
because it captures **only the articulation**: the baked local rotations reproduce the per-bone motion, but the
root flight and scale sweep are the runtime draw args the effect program feeds `Hi_DrawSummonModel` and are
**not offline-decodable for a native cast** — so T1b must *also* read `+0x40` at runtime, re-introducing the
exact staging term FLIGHT never had. It is strictly more moving parts for less coverage (T1 §2.b). Its real
role is the **Blender authoring surface** (§3), not the runtime engine.

### 1.3 The fidelity ceiling, stated plainly

- **Hybrid ceiling = MED-HIGH.** Faithful articulation + root flight + scale + camera + clock, all PROVEN-mechanism
  or PROVEN-read-path. Residuals: (a) the effect-depth regime (the one true ceiling vs native), (b) modern Unity
  shading vs PS1 look, (c) ~15 fps native-tick sampling, (d) a one-time PSX→Unity calibration. None re-opens the
  overlay's failure.
- **Native (T2) ceiling = HIGHEST** — *it is the creature*: exact stock skeleton + motion + native PSX camera +
  per-mesh hide/ABR/texanim, per-poly depth-correct. But it pays the full cost (§1.4) and is held **in reserve,
  per-summon**, only when the offline depth check proves an effect must pass through the creature volume.

### 1.4 Why native (T2) is reserve, not target — the geometry blocker is CLOSED, the gate is elsewhere

T2 re-scoped the native swap and closed the piece everyone feared: **the id-5 model-image geometry write is
PROVEN round-trippable and PROVEN writable** (`ef_geom_writer.py`, committable):

- 24/24 stock creature GEOM blocks parse→serialize **byte-identical**; 135,728/135,728 primitive records across
  1005 blocks re-emitted from decoded fields, **0 mismatches**; the full id-5 image re-assembles with exact
  header-offset recomputation (`firstBlock`/`modelBytes`/`motion[0..7]` all MATCH); a **novel** block (our own
  verts/faces on a 93-bone skeleton) passes every native structural law (`model_prepare 0x7120`'s relative-offset
  relocation, the chain-closure identities, the ≤7000 verts / ≤6 parts / ≤`0x50000` budgets). The feared W5
  blocker is **not** the bottleneck.

What remains for a native swap is **not** the geometry: (a) the **W0 load-gate** — does a mod-folder
`ef###.bytes` override even load? — source-traced (`SFX.cs:1974-1979` → `AssetManager.cs:541-627`,
`SFXData.cs:170`) but **never cast-tested**; a $0 2-cast experiment; (b) texture/CLUT emission (W3, LOW);
(c) one cast to clear the opaque fields; (d) the same rig conformance the hybrid needs anyway. **And the
failure mode is unrecoverable:** per T3-8 (CONFIRMED, one precision note) the DLL **never throws a catchable
exception** — a bad rig either **renders wrong silently** (parent≥child, wrong mesh ordinal, >6 parts, >7000
verts) or **hangs forever** at the `"HIRAISHI ERROR:"` stub (`0x151a0`/`0x151f0`, an infinite oscillating
loop reached from 42 sites in the summon subsystem) on the NULL-data path. Recovery needs a debugger, so every
native container must be **offline-linted before it ships**. **Run W0 early** (it is free and de-risks the
entire depth ceiling), but keep native deferred and per-summon.

---

## 2. THE PIPELINE (D1) — engine hooks, kit surface, milestone ladder

### 2.1 The engine hook — a new `memoria-patches` managed feature ("s54"), never a patched DLL

A managed change to open-source `Assembly-CSharp`, one step past the passive s52/s53 probe (it *renders content*
and performs a runtime write into plugin state), so it is an **owner go/no-go FEATURE** — say that in the commit
message. It co-locates with the s53 read inside `SFXDataMesh.Runtime.Render` at **`SFXDataMesh.cs:659`** (right
after `SfxMeshProbe.LogModels()`); by that point this frame's native Draw has run, `*(SummonData+0x38)` holds
this frame's world matrices, the `Camera camera` is resolved (`:635`), and `currentCameraEngine=SFX_PLUGIN`
(`:607`) so the camera is the native one.

**The per-frame loop** (PLAUSIBLE build, PROVEN read path — the read is exactly what `SfxMeshProbe.cs:479-497`
already does):

```
base   = GetModuleHandle("FF9SpecialEffectPlugin.dll")
rec    = base + 0x220830          // summon record (LENGTH 1) — Hi_RegisterSummonModel@0x15ee0
active = ReadByte(rec + 0x50)     // 0 => no summon this frame → bail
sData  = ReadIntPtr(rec + 0x00)   // -> SummonData
bones  = ReadIntPtr(sData + 0x38) // the 93 world matrices; 0 => never drawn → bail
for k in 0..92:                   // 32-byte PSX MATRIX: s16 3x3 /4096 @+0x00, s32 t @+0x14, stride 0x20
    smr.bones[k].position = PsxToUnityPos(M.t)   // ABSOLUTE world pose — matrices already composed (T1 §1.2, PROVEN)
    smr.bones[k].rotation = PsxToUnityRot(M.R)    // node builder writes +0x38 every Draw @0x7820:0x7842
```

- `smr` = the `SkinnedMeshRenderer` of our FBX, loaded once via `ModelFactory.CreateModel(fbxPath,…)`
  (`SFXDataMesh.cs:769`) with its `Animation` component disabled. **The existing FileList path exposes NO
  settable bones** (a grep of `Battle/SFX/` finds zero `SkinnedMeshRenderer.bones`/`bindposes` refs — PROVEN in
  D1-VERIFY), so this small custom renderer that writes bone `Transform`s each frame is **genuinely new code**,
  ~60–120 lines.
- Writing each bone's **absolute world** transform overwrites our model's own parenting every frame, so only
  *correspondence* (bone `k` ↔ node `k`) and *bind pose* matter — no runtime hierarchy walk (T1 §2.a). This is
  why the whole pose (articulation ∘ root TRS ∘ authored scale) arrives in one read: `+0x38` is the output the
  GTE consumed, the node builder `0x7820` writes every entry as that node's WORLD transform each Draw (PROVEN,
  re-disassembled in T1 §1.2 and the T3 §5b fresh disasm).

**Hide the native creature body** (PROVEN mechanism, D4): assert the total-hide mask each frame before the
native draw — `WriteInt32(sData + 0x20, (1 << meshCount) - 1)` = **`0x3` for Bahamut's 2 meshes**. The mask at
`SummonData+0x20` is re-read on every mesh of every frame (`0x17910-0x17919`), is **summon-only** (`Hi_DrawEffModel`
has zero refs to it), and hiding the body leaves every swirl/beam/fire-column effect rendering with bone-parented
props still following the native skeleton (which keeps computing under a hidden body — the node builder rebuilds
`+0x38` irrespective of the mask). A census of all 24 creature-bearing effects found `meshCount ∈ {2,3}` (max 3),
so `0xFFFFFFFF` is also a safe total-hide (higher bits inert) — prefer the derived value for lintability. The
managed `HideMeshes=` SFXKey split (proven in FLIGHT) is the **safer first cut** that needs no native write —
Milestone 1a uses it.

**The PSX→Unity calibration** (PLAUSIBLE, **ZERO free parameters**): rotation = the s16 3×3 ÷ 4096 with columns
1,2 negated (the `diag(1,-1,-1)` handedness flip the plugin itself applies, node builder root branch `0x797a`);
translation = the s32 triple mapped `(tx,-ty,-tz)/scale` into `Camera.main`'s world space. **The scale factor +
exact sign are calibrated ONCE** against the s53 `BONES`/`PRIM` screen AABB — a validator with zero free
parameters, not a search (D3 already reconstructs the offline pose to ~1% on 2 of 3 sorted axes). The 0.02→3.0
scale sweep is already inside the `+0x38` columns, so it reproduces automatically — the exact term
`root_reproject.py:43/75` silently discarded in FLIGHT.

> **M0 UPDATE 2026-07-23:** the guessed `(tx,-ty,-tz)/scale` map above is REFUTED — it reprojects 88×
> worse than the correct map on real bytes. The verified calibration (zero free parameters, DERIVED from
> `SFX.cs:1603` + `PsxCamera.cs:103-120`, then validated on 5 logged casts): `PsxToUnityPos(tx,ty,tz) =
> (tx,-ty,tz)`, **scale exactly 1** (no `/256`/`×256` — pinned to 1.0 within ±10% by an adversarial
> re-derivation); rotation = `B·R·B` with `B=diag(1,-1,1)` (a *world* basis change, not the view-matrix's
> extra Z-flip). ~7.5% of frames (the ~3.0× climax hold, f153-177, 25 frames, reproduced on every session)
> store an intrinsically IMPROPER matrix (det<0) — a real reflection in the PSX data, not a bug — so
> `PsxToUnityRot` needs a `det<0` guard before quaternion extraction. See `m0/CALIBRATION.md` (§6 states
> the refutation numerically) + `m0/VERIFY_CALIBRATION.md` (independent re-derivation, HIGH confidence,
> not refuted).

### 2.2 The shared prerequisite — same-skeleton rig conformance (BOTH paths need it)

Every faithful path — hybrid, native, or baked-clip — needs **our mesh skinned to a rig that reproduces the
dragon's rest pose and 1:1 node correspondence** (T1 §3, T2 §3, T3 §2.3). This is the one irreducible creative
cost and the natural cost of "wear the dragon's animation." The kit already emits skinned FBX in exactly this
shape (`models/fbx_skin.py` names one bone `bone{NNN}` per node, digits = the FF9 node number, and recomputes
bind poses from each bone's rest transform).

**Deliver `summon-rig-ref` (= the `summon-export` forward exporter, §3).** It reads the USER's own `ef###.bytes`
(local, SCRATCH) and emits a **93-bone rig reference `.glb`** (bones `bone000..bone092`, parent indices, bone
lengths → local `(0,0,length)`, a chosen rest pose) that the user opens in Blender and skins their mesh onto.
Drive is then **1:1 by node index** (hybrid: world matrices land on `smr.bones[k]`; baked-clip: `.anim` curves
bind by bone name). **Topology caveat (SPECULATIVE — DESIGN risk, flag to the user EARLY):** same-skeleton
authoring is pleasant only for a creature whose silhouette suits a 93-node long-necked flyer (another
dragon/quadruped/serpent). A humanoid Thomas on a dragon rig may pose correctly and still look wrong — an art
decision, not an engine failure, surface it before the user invests in skinning.

> **M0 UPDATE 2026-07-23:** the FBX-path recon landed — the complete hop-by-hop `FileList.txt` →
> `.sfxmodel` → FBX/clip resolution chain is now pinned file:line, incl. the load-bearing
> **donor-FileList replacement law**: writing `FileList.txt` (or a `Model` line) into a real donor's OWN
> `ef{donorId:D3}/` folder silently replaces the ENTIRE native cast with our JSON mesh (`SFXData.cs:156-181`,
> an `if (mesh != null) return` fires before `loadingQueue.Enqueue` ever runs) — fatal to the hybrid, which
> needs the native engine actually running so `+0x38` has real data. The rule: custom `FileList.txt` content
> must live on a SEPARATE, PRIVATE effect id only, never the donor's own folder — exactly rung 7 /
> `build_thomas.py`'s existing convention (`ef084`), now derived from source rather than just precedent.
> See `m0/FBX-PATHS.md`.

### 2.3 The kit surface — a managed `[[summon]]` lane, kept SEPARATE from the native family

- **`[[summon]]` block / `summon-transplant` verb (the MANAGED lane — the recommendation).** Inputs: the user's
  retargeted FBX + a donor summon id. It (a) runs `summon-rig-ref` to emit the local rig, (b) deploys the FBX into
  the effect's model slot, (c) writes the s54 drive-feature manifest (which summon slot to drive with which model,
  gated like the probe). New kit modules: `summons/build.py` (Model-struct adapter), `summons/motion.py` (offline
  clip decoder for the baked-clip sibling), `summons/export.py` (glTF emit, reuses `models/gltf.py`).
- **The native read/fork family (a SEPARATE surface).** `summon-inspect` / `summon-disasm` / `summon-fork` share
  `ef_container.py` + `ef_geom_writer.py` (both committable, both proven). Different provenance rules, different
  failure modes — **do not merge them into `[[summon]]`.**

### 2.4 The milestone ladder — smallest thing first, de-risked, verbatim-first

**Milestone 0 — the offline camera/reprojection + depth gate (1 cast, ZERO new content) — DO THIS FIRST.**
Take one instrumented Bahamut cast on the bench (field 30300, id 194) with the **already-deployed s53 probe**
armed. Run offline: (a) project one controlled world point through BOTH the logged managed `VIEW·PROJ` and the
native `PSXCAM` (`M` + OFX/OFY/H) → predicted screen delta ≈ 0 (this settles the horizontal/widescreen
pixel-equality left open in §1.1); (b) confirm managed `VIEW` == native `PSXCAM` `M` every frame (no live phase
lead beyond the ≤1-step residual); (c) fix the PSX→Unity scale/sign from the `BONES`/`PRIM` AABB; (d) scan
whether any effect `PRIM` occupies the creature's screen region at a nearer depth (the hybrid-vs-native decision
per summon). *Cost: LOW, read-only, provenance-clean. Unblocks everything below.*

> **M0 UPDATE 2026-07-23:** items (a)+(b)+(c) are DONE and adversarially verified — CONFIRMED, not refuted.
> (a)+(b): a managed object at `PsxToUnity(creature world point)` projected through the logged `Camera.main`
> lands within p95 2.96px horizontal / 7.16px vertical / 7.65px radial of the native creature (320×240
> frame) — the horizontal/widescreen axis turns out to be the *tighter* axis, not the looser one this
> section worried about; the D4 camera-track fallback is NOT needed. (c): the PSX→Unity map is
> `(tx,-ty,tz)` scale 1, `B·R·B` rotation (§2.1's update above). See `m0/CAMERA-MATCH.md` +
> `m0/CALIBRATION.md`, both independently re-verified (`m0/VERIFY-CAMERA-MATCH.md` +
> `m0/VERIFY_CALIBRATION.md`). Item (d) — the depth gate — is PENDING: it needs a cast with
> `[SfxProbe] CapturePrims=1` armed (not yet armed on any captured log); the arming protocol is written
> and ready to execute → `m0/CAST-PROTOCOL.md`. Also carried forward from risk #4 below: the
> ≤1-native-substep VIEW/M sampling residual remains the thing to watch on the M1a cast, not yet retired.

**Milestone 1a — our model rides the dragon's CAMERA (reuse rung-7 verbatim, ZERO new engine code).** FileList a
proven rung-7 FBX into a Bahamut donor cast and hide the native body with the managed `HideMeshes=` split. Our
model plays only its own idle but **inherits the native camera** — banks/zooms/cuts. Isolates the
camera-inheritance proof + the body-hide + the depth residual in-game with no new engine code. *Cost: LOW.*

**Milestone 1b — THE FAITHFUL MVP: our model + the dragon's real MOTION.** Land the **s54 hybrid drive feature**
(§2.1). The user skins their mesh onto the `summon-rig-ref` rig, the drive loop poses it each frame from `+0x38`,
the body is hidden. **Exit / smallest faithful render: our mesh flaps, banks, shrinks, and flies with the
dragon's actual per-frame motion, through the dragon's actual camera, in one cast on the bench.** *Cost: MED.*

**Milestone 2 — fidelity polish + the Blender authoring surface (§3):** the s46 render-rig lessons
(live-silhouette fit, body-blend zoom, lighting), the per-summon depth verdict, and the Blender round-trip
(`summon-export` → retarget → `summon-import`). *Cost: MED, mostly kit code + proven routes.*

**Milestone 3 — the native ceiling (T2), ONLY if the depth residual bites.** If M0/M1a show an effect must pass
*through* the creature volume, escalate that summon to the native model-package swap. **Run W0 first** (the $0
2-cast load-gate). If W0 passes: `ef_geom_writer.py` (PROVEN) + header math (PROVEN) + texture/CLUT emit (W3,
LOW) + the offline geom linter → per-poly depth-correct. Failure mode is a silent hang → **never ship an unlinted
container.** *Cost: HIGH. Deferred, per-summon.*

### 2.5 Ranked by unblock-value ÷ cost

| # | action | cost | unblocks |
|---|---|---|---|
| 1 | **M0 — offline camera/reprojection + depth gate** (armed s53 probe, 1 cast) | 1 cast, read-only | the whole hybrid: camera inheritance *measured*, PSX→Unity calibration fixed, depth residual read |
| 2 | **`summon-rig-ref` / `summon-export`** (shared 93-bone rig, committable) | LOW–MED | BOTH paths — the user can start skinning immediately |
| 3 | **M1a — rung-7 FBX + managed HideMeshes in a donor cast** | LOW, no new engine code | camera-inheritance + body-hide + depth residual, proven in-game |
| 4 | **M1b — the s54 hybrid drive feature** | MED (memoria-patches) | THE faithful transplant |
| 5 | **W0 — the native load-gate** ($0, 2 casts) | $0, 2 casts | ALL of the native lane; de-risks the depth ceiling early |
| 6 | **M2 — polish + Blender round-trip** | MED | the user's second ask + offline-editable clips |
| 7 | **M3 — native model-package swap (T2)** | HIGH | per-poly depth-correct effects — only for body-wrapping summons |

---

## 3. THE BLENDER ROUND-TRIP (D2/D3) — exporter, retarget, return path

**Status: buildable and small, grounded in the D3 real-bytes spike.** T3 established feasibility; D2 turned it
into a numbered module plan; D3 drove the thesis into actual `ef227` bytes. It is the user's second ask ("export
into Blender") *and* the provenance-cleaner sibling of the live lane — the clip is authored offline from the
local container, never dumping per-bone runtime state. **The two lanes are complementary:** the live-matrix
hybrid is the runtime engine; the Blender round-trip is its authoring surface. Both need the SAME two things D2
delivers — a compatible skeleton (`bone000..bone092`) and a decoded clip.

### 3.1 What parsed export-ready on real bytes (D3, PROVEN)

The D3 spike (`transplant_spike.py`, committable) cross-checked the offline decode against the live s53 BONES
probe on `ef227` (Bahamut), generalised on `ef261` (Odin) with `ef000` as the negative control:

- **Skeleton (PROVEN, export-ready):** 93 nodes, a forward-referencing parent+length tree (`parent<child` in
  92/92 links, middle byte 0 in 92/92, 66 distinct parents = genuinely branched), bone lengths sane. Matches the
  live probe `n=93` across the whole cast. Odin generalises (97 nodes, 96/96 forward, 75 parents).
- **Skinning (PROVEN, export-ready):** rigid, run-length, **exactly one bone per vertex** (`maxVtxIdx==nVert-1`,
  both meshes). This drops straight into the kit's Model struct as `weights=[[(bone,1.0)]]` — no weight solve, no
  top-4 cap, no cluster ambiguity. (Confirms T3-1 and T3-2, both CONFIRMED in verification.)
- **Motion reader (PROVEN structure):** all 8 Bahamut clips decode and **tile exactly** (0 gaps / 0 overlaps),
  frame counts exact `[24,30,26,48,40,68,82,28]`, angles well-formed; animated fraction 22.6–56.3% matches M5's
  independent measure. **The decode reconstructs the creature:** the offline scale-1 skeleton (clip0/f0) has
  sorted axis spans `[614, 2657, 4437]` vs the live probe's nearest at-scale-1 frame `[740, 2619, 4431]` —
  ratios `[0.83, 1.01, 1.00]`, two of three axes to ≤1.4% from bytes alone. The scale sanity band (42→7771)
  independently confirms M5's authored 0.02→3.0 sweep.
- **Bind-pose construction (PROVEN math, T3-3 CONFIRMED with fresh disasm of `0x80aa..0x83c7`):** node rest TRS
  = `(restRot[b], (0,0,length[b]))`; bind-pose verts = `W[b]·pool_vertex`; inverseBind auto-recomputed by both
  glTF and the FBX importer. Posing the bound mesh by any clip reproduces the renderer's `W_anim[b]·pool_vertex`
  exactly — coordinate- and clip-independent. Rest choice (identity for MVP, or clip[0]f0 for a recognizable
  dragon) is a self-consistent design knob, not a gap.

### 3.2 The one previously-fuzzy piece is now DECODED (D3 → T3-4-VERIFY)

D3 flagged one fuzzy item: the exact **PSX RotMatrix Euler composition order** (load-bearing for a faithful
DCC→clip *exporter*, though NOT for the live-matrix hybrid, which reads pre-composed matrices). **T3-4-VERIFY
closed it** with fresh disasm: the three per-axis builders are `Rx@0x37a0`, `Ry@0x3850`, `Rz@0x3910` (textbook
per-axis matrices, angle scaled by exactly `2π/4096`), composed in that call order (`0x7d8a/0x7d9a/0x7daa`) into
an fp12 identity seed. The **only** residual determinations are trivial: which IAT thunk is cos vs sin, and
pre- vs post-multiply in `0x3450`. The correctness is **free to validate offline** against the probe's already-
logged composed bone-0 matrix — the existing on-disk log already has 480 dual-logged (anchor + composed) Bahamut
frames, and a spot check confirmed `composed = anchor · (proper rotation)` to within 1/4096 quantization
(`‖RᵀR−I‖≈0.0026`, `det≈+0.998`). So the exporter's one genuine new decode is **de-risked to a bounded read
with a free, airtight validator — zero playtests.** (The validation reads bone 0 ONLY; dumping `bones[1..92]` is
BLOCKED — that reconstructs the stock skeletal animation as a redistributable asset.)

> **M0 UPDATE 2026-07-23:** the residual determinations flagged above are now CLOSED. `R_local =
> Rz(az)·Ry(ay)·Rx(ax)`, STANDARD cos/sin (cos on the diagonal), angles × `2π/4096`, composed by
> PRE-multiplication, no transpose — confirmed two independent ways (a >1000× log-margin discrimination
> over 1072 matched frames across all 8 candidate conventions, AND direct disasm of `0x37a0`/`0x3850`/
> `0x3910`/`0x3450`/`0x7d8a-0x7daa`). `transplant_spike.py::_rotmat` is now fully verified correct
> verbatim — adopt as-is. See `m0/EULER.md` (incl. the closed-form inverse decompose the exporter needs).

### 3.3 The exporter — "`model-gltf` for summons" (T3-5, CORRECTED)

The forward tool reuses the kit's proven glTF machinery. The honest scope (per the T3-5 correction): it reuses
the `_gltf_io` buffer/writer and coord helpers unchanged and the per-channel emission math unchanged, but
**requires a refactor** — extract `export_gltf`'s emission body into `emit_model_gltf(model, clips, buf, out)`,
parametrize the clip source, and bypass the p0data loads and `bone_labels`. There are **THREE** p0data coupling
sites to sever (not two): `read_model` (168), the p0data5 load + `_select_anim_keys` (322-323), and `read_clip`
(328, inside the emission loop). New code = the motion decoder + the Model-struct adapter + this factoring.
Confirmed for free: the clip-shape match (the animation loop `gltf.py:324-382` walks `clip["bones"]` and emits
rot/trans/scale channels keyed by bone number — a summon clip is that exact shape), the writer/coord-helper
reuse, and that the emitted `.glb` opens via the add-on's unchanged **Import Model** (`import_scene.gltf`).

Concrete module ledger (D2): `summons/motion.py` (~150 LOC, the one genuine decode, self-validating),
`summons/build.py` (~120 LOC, adapter), `summons/export.py` + the `emit_model_gltf` factor-out (~60 LOC + a
behavior-preserving refactor, regression-guarded by a `model-gltf zidane` byte-compare), `summons/deploy.py`
(~120 LOC, MED risk — the return packaging).

### 3.4 The return path — the FileList FBX route (T3-6, CONFIRMED PROVEN mechanism)

The user retargets their mesh onto the dragon's `bone000..bone092` armature (weights to those bones, **keep the
names + hierarchy** — rename/reparent breaks binding), deletes the dragon mesh, keeps the armature + clips, and
exports a `.glb`. `summon-import` then writes the FBX + the dragon's `.anim` clips + a `.sfxmodel` into the
SpecialEffects model slot, fired by a battle `.seq` — the rung-7 substrate, DLL-free, provenance-clean. **Why
the retarget "just works":** Unity `AnimationClip`s bind curves **by bone hierarchy PATH**; the dragon's baked
clip keys `bone000/bone001/...`, and `ModelImporter.CreateCustomModel` builds exactly that nested hierarchy
(`:338` `bone{boneId:D3}`, `:349` child parents to `bones[parentIndex]`), so a user mesh on the same armature
resolves every curve with **zero remap** (independently re-derived from the DLL-side C# in T3 §8.2). **Honesty
caveat (does not refute):** "rung-7 proven" means an animated custom FBX renders in a live battle via FileList —
it does NOT mean "the dragon's decoded clip on a retargeted mesh in a summon cast" has literally run; that
composition still owes the §3.2 decode + a first cast (M0/M1b gate it offline first).

> **M0 UPDATE 2026-07-23:** the exact FBX/clip path-resolution chain this return path rides on is now
> fully pinned (`m0/FBX-PATHS.md`, hop-by-hop, file:line) — closing risk #7 below's open item. Confirms the
> `Model {name}` (bare, no `/`) / `Animations[].Path` grammar, and that **the `.sfxmodel`+`FileList.txt`
> must live on a PRIVATE effect id, never the donor's own `ef{donorId:D3}/` folder** (writing it there
> silently swaps out the whole native cast — the donor-FileList replacement law, §2.2's update above).

### 3.5 The staging layer — say it out loud so no playtest is wasted (T3-7, CONFIRMED PROVEN)

The baked clip is the **skeletal layer ONLY**. The root-translation span of every axis of all 8 Bahamut clips is
**≤246 units** (falsification test for "staging is in the clip": refute-if >1000; **not met** — 246 ≪ 1000). The
big staging — the fly-down, the measured **72,960-unit** Z fly-by, the **0.02×→3.0×** perspective scale — is the
per-frame anchor `(rot,pos,scale)` the `.seq`/MIPS program feeds `Hi_DrawSummonModel` (composed into `+0x40` by
`pose_eval@0x186a0`), **NOT in the clip**. The camera is a third independent native layer (H sweeps 256→512, the
47°→24° push-in). **A retargeted FBX playing the baked clip alone flaps exactly like the dragon but does not fly
across the screen** — do not sell the clip as the whole cinematic. Two ways to supply staging for a standalone
managed cast, neither from the Blender file: (a) authored `.sfxmodel` Movement/Rotation/Scaling curves,
recoverable offline from the s52 probe's already-logged anchor rows (use the column-norm scale — the term
`root_reproject.py` drops); (b) the donor hybrid (run the native donor, `HideMeshes` its body, our FBX renders
inside its camera + staging). **The live-matrix hybrid (§1) sidesteps this entirely** — the `+0x38` read already
folds the staging into every bone's world matrix, which is precisely why it dominates T1b for a native cast.

---

## 4. RISKS + OPEN QUESTIONS (ranked) + the cheapest next experiment

**The cheapest next experiment (do this first): Milestone 0 — the offline camera/reprojection + depth gate.**
One instrumented Bahamut cast with the already-armed s53 probe, then all analysis offline. It is read-only,
ships zero content, and simultaneously (a) converts "camera faithful by construction" into a measured number
incl. the horizontal/widescreen axis, (b) fixes the zero-free-parameter PSX→Unity calibration, (c) reads the
depth residual that decides hybrid-vs-native per summon, and (d) exercises the free bone-0 Euler validation. It
retires the two PLAUSIBLE mechanisms the hybrid rests on without a single playtest.

Ranked risks (each stated with its falsifier and its fix path):

1. **P4 — the effect-DEPTH residual (PLAUSIBLE, the true hybrid ceiling).** An effect prim occupies the
   creature's screen region at a nearer depth on framed frames ⇒ the hybrid sorts it wholesale wrong; that
   summon needs native (T2). **Measurable offline from M0.** This is the only fidelity axis where native beats
   the hybrid.
2. **Camera horizontal/widescreen pixel-equality (PLAUSIBLE).** Vertical is proven-by-construction (OFY=120);
   horizontal is aspect-scaled and **must be measured at M0**. Falsifier: managed `VIEW·PROJ` ≠ native `PSXCAM`
   on a control point. Fix if it fails: drive `Camera.main` from the decoded native camera track (D4's camera
   authoring lane is fully specced — `camera_codec.py` already round-trips the format byte-exact).
   > **M0 UPDATE 2026-07-23:** MEASURED, CONFIRMED — horizontal p95 2.96px, in fact the *tighter* axis of the
   > two (vertical p95 7.16px, attributable to the creature's larger vertical excursion on this cast, not to
   > `PROJ12` per se — both axes algebraically reduce to the same `110·PROJ11==H` condition). D4 fallback
   > not needed. See `m0/CAMERA-MATCH.md`.
3. **P5 — topology / DESIGN risk (SPECULATIVE).** A humanoid mesh on a 93-node dragon rig may look wrong even
   when posed correctly. Not an engine failure — **flag before the user skins.** No engine falsifier; it is an
   art call.
4. **The live render-pass race (PLAUSIBLE).** Does writing 93 bone-`Transform`s at `SFXDataMesh.cs:659` land
   before Unity's skinning pass, and does our SMR render in this camera pass while `SFXRender.Render`
   saves/restores `worldToCameraMatrix` (`:130/:135`, `Runtime.Render` `:636/:678`)? T4 §1.4 argues no race
   (both settle to the final tick). The one thing to confirm on the M1a cast. Falsifier: our model lags/leads
   the effects by a visible step.
   > **M0 UPDATE 2026-07-23:** a related residual was measured (not this exact race, but its sibling): the
   > probe's VIEW/M sampling shows a ≤1-native-tick slip at the ~15 hard cuts (up to ~500 world units on
   > translation; rotation still matches to fp12) — a probe-sampling artifact, not a broken relation, but
   > still the thing to watch for on the M1a cast per this risk's own falsifier. See `m0/CAMERA-MATCH.md`
   > Part (b).
5. **The exporter's final Euler bits (PLAUSIBLE, bounded).** cos-vs-sin thunk + pre/post-multiply in `0x3450`.
   Free bone-0 validation against the existing log; a mismatch names the wrong axis. Blocks only the DCC→clip
   *exporter*, not the live hybrid.
   > **M0 UPDATE 2026-07-23:** CLOSED, zero playtests — `Rz·Ry·Rx`, standard cos/sin, pre-multiply, confirmed
   > by log discrimination (>1000× margin over 8 candidate conventions) + direct disasm. See `m0/EULER.md`.
6. **P6 — W0 native load-gate (PLAUSIBLE, only matters if native is needed).** Does a mod-folder `ef###.bytes`
   override load? Source-plausible, never run. $0 2-cast test. Only gates the T2 reserve path.
7. **`.sfxmodel`/SpecialEffects slot path (PLAUSIBLE, MED — the one Blender-lane unknown to pin before coding
   `summons/deploy.py`).** Where `ModelFactory.CreateModel` + `AssetManager.Load<AnimationClip>` probe for a
   summon-effect FBX/clip. Rung 7 proved an FBX renders via FileList; read `ModelSequence.LoadFBX`
   (`SFXDataMesh.cs:976-1029`) to pin the exact path before coding D.
8. **Native opaque fields + hide-mask initial value (runtime-only OPEN, only for T2).** Settled by one probe row
   logging `DATA+0x20` on the first Draw. Not gating the hybrid.

**What is NOT a risk (closed):** the geometry write (PROVEN byte-identical + novel-block-valid), the container
rebuild (371/372 byte-identical), the skeleton/skinning decode (PROVEN on real bytes), the bind-pose math
(PROVEN, twice-disasm'd), the camera *stamping* mechanism (PROVEN in source, C1 CONFIRMED), the by-path clip
binding (PROVEN mechanism, T3-6 CONFIRMED).

---

## 5. PROVENANCE LEDGER — committable code vs local-only stock content (STRICT this round)

This round touches stock GEOMETRY + ANIMATION, so the line is drawn hard. **Reading the DLL + game data to
UNDERSTAND is sanctioned. A committable format PARSER/EXPORTER is CODE and is fine. Extracted stock CONTENT is
Square-Enix content and is NOT committable** — it lives only under `C:/gd/SCRATCH/summon-transplant/` (local,
gitignored), exactly the battle-import / verbatim-fork precedent.

| artifact | class | where it lives |
|---|---|---|
| `ef_container.py` (parser, 372/372), `ef_geom_writer.py` (geom writer, byte-identity harness), `transplant_spike.py` (spike) | **committable CODE** — read a caller-supplied local blob, embed zero game bytes | the repo |
| `summons/motion.py`, `build.py`, `export.py`, `deploy.py`, the `.sfxmodel` emitter, the CLI verbs, the `gltf.emit_model_gltf` factor-out, `camera_codec.py` SFX-flavour extensions | **committable CODE** (parsers/adapters/writers/refactors) | the repo |
| the **s54 hybrid drive feature** | **committable CODE** — a *managed* patch on `memoria-patches/` performing passive `+0x38` reads to drive OUR mesh + one runtime hide-mask write; ships no asset bytes, calls no plugin export | `memoria-patches/` (owner go/no-go) |
| extracted `ef###.bytes`; the exported stock-creature `.glb` (dragon mesh/rig/baked clips/textures); the `summon-rig-ref` rig | **stock content → LOCAL-ONLY** | `C:/gd/SCRATCH/summon-transplant/` |
| the USER's retargeted model + the clips/FBX they build into their OWN mod folder at deploy time | **the user's — verbatim-fork precedent** | the user's mod folder |
| reading the creature's per-frame bone matrices to **DRIVE our own mesh** (hybrid), or bone-0 to **VALIDATE** the offline decode | **sanctioned** — choreography/pose class, identical to the camera track (s48) and root (s52) | — |
| **dumping `bones[1..92]` across a cast** as a redistributable animation asset | **BLOCKED** — reconstructs the stock skeletal animation | — |
| a patched / redistributed `FF9SpecialEffectPlugin.dll` | **NEVER** — engine work stays on `memoria-patches/`; the hybrid + Blender lanes need NO plugin DLL edit | — |

**Hard CLI rule:** `summon-export`/`summon-rig-ref` **default their output to `C:/gd/SCRATCH/summon-transplant/`
and REFUSE to write a stock-creature export into the repo or a distributed mod folder.** `summon-import` writes
the user's OWN retargeted model into the user's OWN mod folder — that is theirs. The **deliverable is a PIPELINE
+ TOOLS**; the user runs them on their own install. Every native claim in the phase slices cites `fn@rva`; every
managed claim `file:line`; no stock geometry, animation payload, texture, or container bytes were written into
the repo across the whole round.

---

## 6. EXECUTIVE SUMMARY (for the orchestrator)

**Is a faithful transplant real? YES.** The overlay's core failure — a rigid billboard that can't read as a
creature flying/banking/shrinking/rolling — is dissolved by the **HYBRID**: our own skinned model posed each
frame by the dragon's real 93 world-matrices read live from `*(SummonData+0x38)`, rendered through
`Camera.main`, which the plugin stamps with the native per-frame camera. One read carries articulation + root
flight + the 0.02→3.0 scale sweep in perfect lockstep, and it ships zero stock bytes.

**The decisive finding (CONFIRMED, twice re-derived from source): the native camera is inherited by the MANAGED
path too, not only the native slot** (`SFX.UpdateCamera` stamps `Camera.main` every frame; `PsxProj2UnityProj`
reproduces the native GTE `OFY=120` by construction). So faithfulness of *motion and camera* does **NOT** require
the native slot. The native slot (T2) buys exactly one thing the hybrid lacks — per-poly depth interleave with
the screen-space effect prims — which matters only for effects that physically wrap the creature body and is
**measurable offline before any playtest.** Hybrid is the target; native is reserve, per-summon. (Its feared
geometry-write blocker is CLOSED — `ef_geom_writer.py` re-emits 24/24 creatures + 135,728/135,728 records
byte-identical and passes a novel block — but it stays deferred behind the untested $0 W0 load-gate and an
unrecoverable silent-hang failure mode.)

**Recommended path + first milestone:** build the s54 managed hybrid drive feature; but the **cheapest first
step is Milestone 0** — one instrumented Bahamut cast with the already-armed s53 probe, then all-offline: it
measures the camera match (incl. the horizontal/widescreen axis, the one honest caveat on "same pixel for
free"), fixes the zero-free-parameter PSX→Unity calibration, and reads the depth residual that decides
hybrid-vs-native per summon — zero content, zero playtest risk. Then **M1a** (our model + native camera + hide,
no new engine code) → **M1b** (the faithful MVP: our mesh + the dragon's real motion + native camera in one
cast). The one irreducible creative cost, shared by every path, is skinning the user's mesh onto a 93-bone
`bone000..bone092` rig (`summon-rig-ref` emits it locally); flag the humanoid-on-dragon-rig look as a design
risk before the user skins.

**Blender round-trip status: buildable and small, grounded in a real-bytes spike.** The skeleton, rigid
one-bone-per-vertex skin, and motion reader all parsed export-ready on `ef227` (offline pose reconstructs the
live creature to ~1%). The one previously-fuzzy item — the Euler composition order — is now **DECODED**
(Rx@0x37a0 / Ry@0x3850 / Rz@0x3910 in that order; only cos-vs-sin and pre/post-multiply remain, both trivial,
both free to validate against the existing probe log). Forward tool = `summon-export` ("`model-gltf` for
summons" — reuses the kit's glTF writer behind a small `emit_model_gltf` refactor severing three p0data sites);
return = the proven rung-7 FileList/`.sfxmodel` route where the dragon's clips bind to a retargeted mesh **by
bone-path for free**. The baked clip is the skeletal layer only — the fly-by/scale staging is a separate layer
(authored `.sfxmodel` curves or the donor hybrid), which the live-matrix hybrid sidesteps entirely. Committable
throughout; every stock-derived byte stays local under `C:/gd/SCRATCH/summon-transplant/`; no patched DLL.
