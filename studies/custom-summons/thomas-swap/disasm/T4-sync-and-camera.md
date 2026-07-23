# T4 — ANIMATION SYNC + CAMERA / EFFECT INHERITANCE

**The slice:** whatever delivery path wins (native summon slot T2, managed FileList FBX T1b, or the
bone-matrix HYBRID), the transplanted model must stay in **lockstep** with the native camera cuts,
the effects, and the timing — the exact lockstep a hand-choreographed overlay lacked over 10 FLIGHT
iterations. This slice decides the **fidelity ceiling** of each path.

All C# cites are `Assembly-CSharp` relative to `C:/gd/FFIX/Memoria/Assembly-CSharp/`. All RVAs are
image-base-relative to the user's own installed `FF9SpecialEffectPlugin.dll` (x64 `0x180000000`) and
come from **read-only** static analysis. No stock content is quoted; structural facts only.

---

## 0. HEADLINE — the overlay's core failure is DISSOLVED, and the ceiling splits cleanly

1. **The camera is inherited by the MANAGED path too, not just the native slot — and it is faithful by
   construction, not by luck.** During any summon, `Camera.main.worldToCameraMatrix` +
   `.projectionMatrix` are stamped **every frame** from the DLL's real per-frame camera
   (`SFX_UpdateCamera` → 13 floats). The managed `PsxProj2UnityProj` reconstruction is **engineered to
   reproduce the native GTE principal point exactly** (`PsxScreenHeightNative = 220`, `220/2.2 = 100`,
   `top = 120` ⇒ optical axis 120 px from the top = native `OFY = 120`). So a Unity object placed at the
   creature's world point projects to the **same screen pixel** the native creature would — through all 15
   hard cuts and the 47°→24° zoom, **for free**. This is precisely what the overlay had to hand-animate
   and never got right. (§1)

2. **The FORMAT round's "managed VIEW/PROJ diverged from native GTE 88.7 % of frames" is NOT a
   camera-mapping divergence.** It measured **reprojecting the ANCHOR** (`SummonData+0x40`), confounded by
   the wrong datum (anchor ≠ creature silhouette), the wrong instant (an offline log-join across a
   multi-tick frame), and the anchor's own 40 000-unit authored fly-by. A **co-located point** projects
   through managed and native **identically**. The divergence number does not bound a rendered model's
   fidelity. (§1.3)

3. **The clock is already unified.** Native motion advances one sample per native Draw (`rec+0x54`); the
   FileList `Animations` clip is a manual frame-driven sampler keyed on the **same `SFX.frameIndex`**; the
   hybrid samples bones on the native tick. All three stay synced through WAIT/hold beats by
   construction. (§2)

4. **The effects are independent — CONFIRMED for a full-body swap, not just the HideMeshes probe.** The
   summon hide mask is summon-model-only; hiding the creature's body leaves every swirl/beam/fire slot
   rendering, and bone-parented props keep following the native skeleton (which is still computed even when
   the meshes are hidden). (§3)

5. **The ONE residual that separates the ceilings is the DEPTH-COMPOSITING REGIME.** Native effect prims
   are **screen-space** composited (the DLL already did the GTE; `SFXRender.Render` forces
   `worldToCameraMatrix = identity`, `SFXRender.cs:130`); a managed perspective FBX lives in a **different
   regime** and does **not** depth-interleave per-poly with the effect prims. Effects that wrap the
   creature (fire column in front, swirl behind) will sort **wholesale** in front of or behind a managed
   model. Only the **native slot (T2)** — where our model shares the ordering table with the effects —
   removes this. (§1.5, §4)

---

## 1. THE CAMERA

### 1.1 A managed object rendered during a summon IS drawn through the native camera (PROVEN)

The summon gate `SFXData.FixedCameraEffects` (`SFXData.cs:1339-1371`, contains every `*__Full` incl.
`Bahamut__Full`) sets `UseCamera=true` (`BattleActionThread.cs:310`). With that, every frame:

```
SFX.UpdateCamera()                                            SFX.cs:1590-1605
   IntPtr src = SFX_UpdateCamera(isDebug)   → 13 floats @ RVA 0x211df0
   Marshal.Copy(src, array, 0, 13)
   SFX.fxNearZ = array[12]
   camera.worldToCameraMatrix = PsxCamera.PsxMatrix2UnityMatrix(array, cameraOffset)   // VIEW
   camera.projectionMatrix    = PsxCamera.PsxProj2UnityProj(fxNearZ, 65535)            // PROJ
```

`camera` = `Camera.main` or the "Battle Camera" GameObject's camera. In SFXRework this is driven with
`currentCameraEngine = SFX_PLUGIN` set in `SFXDataMesh.Runtime.Begin()` (`SFXDataMesh.cs:607`), and
`SFXDataCamera.UpdateCamera()` (`SFXDataCamera.cs:540-563`) forwards to `SFX.UpdateCamera()`.

⇒ **Any Unity perspective object rendered while a summon is running is projected by the DLL's real
per-frame VIEW + a PROJ derived from the per-frame near-Z.** A model parented in Unity world space is
carried through every camera cut/dolly/zoom **without a single hand-authored keyframe** (A5 §7).

### 1.2 The PROJ reconstruction reproduces the native GTE — it is NOT lossy (PROVEN by constants)

The prior rounds treated `PsxProj2UnityProj` as a "re-derivation with its own off-center convention
(`bottom = h/2.2`)" that might not match the native GTE (`OFX=160 / OFY=120 / H`). **The constants say it
matches exactly:**

* `FieldMap.PsxScreenHeightNative = 220` (`FieldMap.cs:2336`).
* `PsxProj2UnityProj` (`PsxCamera.cs:172-178`): `bottom = 220/2.2 = 100`, `top = 220 − 100 = 120`, then
  `PerspectiveOffCenter(-HalfScreenWidth, +HalfScreenWidth, -100, +120, near=H, far=65535)`.
* In that off-center frustum the optical axis (view `y=0`) maps to `NDC_y = -(top+bottom)/(top-bottom)`
  = `-(120-100)/(120+100)` = `-0.0909`, i.e. `(1-0.0909)/2 · 220 = 100 px from the bottom = **120 px from
  the top** = native **OFY = 120**` (FORMAT §1.2 installs `OFY=120 @0x211FA4`). **Exact.**
* Horizontal is symmetric (`(right+left)/(right-left)=0`), so the horizontal principal point = screen
  center = native **OFX**. (Widescreen scales `HalfScreenWidth`; that is a deliberate pillarbox→widescreen
  choice shared with all battle rendering, not an error.)
* The magnification law matches: managed `NDC_x·HalfScreenWidth = H·x/z`; native GTE `SX−OFX = H·x/z`
  (FORMAT §1.2 RTPS). **`near = array[12] = H` drives the same zoom in both** — this is the 47°→24° zoom,
  carried per frame.

**Verdict: the managed perspective is a faithful reconstruction of the native GTE mapping (VIEW handedness-
flipped, PROJ reproducing OFX/OFY/H). A co-located world point projects to the same screen pixel in both,
to within fp12 rounding.**

### 1.3 Why the "88.7 % divergence" does NOT apply to a rendered model

FORMAT §1.3 / `V-M1-06` measured **reprojecting `SummonData+0x40` (the anchor)** through the logged
VIEW/PROJ and found it off-screen 88.7 % of frames. That is three confounds stacked, none of which is a
camera-mapping error:

| confound | why it does not bound a rendered model |
|---|---|
| **wrong datum** — the anchor is not the creature's silhouette (node 0 of a 93-bone dragon is off-center) | we place OUR model where we choose; the datum is ours to control |
| **wrong instant** — an **offline** join of a logged managed VIEW against the matrix that drew a logged frame, across a frame that ran **many** `SFX_Update` ticks (`SFXDataMesh.cs:576-582`) | a **live** render settles to the final tick's camera + the final tick's prims (§1.4); the phase mismatch is a log-analysis artifact, not a live incoherence |
| **the 40 000-unit fly-by** in the anchor track itself | genuine staging, unrelated to the mapping |

### 1.4 The live-render instant IS coherent (PROVEN mechanism; ≤1-step phase is the only runtime residual)

Per managed frame (`SFXDataMesh.Runtime.Render`, `SFXDataMesh.cs:610-682`): `Load(frame)` loops
`SFX_Update` until `SFX.frameIndex == frame` (possibly many native ticks); then `SFX_LateUpdate` +
`SFXRender.Update` **harvest the FINAL tick's prims** via `SFX_GetPrim`. The managed camera is stamped by
`SFXDataCamera.UpdateCamera()` from `SFX_UpdateCamera`, which reads the **installed** camera `@0x69730`
(A5 §2) — after `Load`, that holds the **final tick's** camera. So model + effects + camera all settle to
the same final tick within a frame. **Residual (runtime-only, cheap to measure):** `SFX_UpdateCamera`'s
gate can install the next keyframe (A5 §4), so the managed camera could lead the prims by ≤1 camera step.
**Falsifiable check with the extended probe:** the logged managed `VIEW` should equal the logged native
`PSXCAM` M **every frame**; if it does, there is no live phase problem.

### 1.5 The ONE camera-adjacent gap for a MANAGED model — the depth regime (PROVEN)

The native effect prims are **screen-space** (`SFX_GetPrim` returns `Int16 x0,y0` already GTE-projected,
A3 §6) with `GzDepth = -otz` as Z. `SFXRender.Render()` draws them with **`camera.worldToCameraMatrix =
Matrix4x4.identity`** (`SFXRender.cs:130`, restored `:135`) — a screen-space regime, **not** the
perspective VIEW. A managed 3D FBX rendered as a real Unity object goes through the **perspective**
VIEW·PROJ. The two regimes do not share a Z axis, so a managed FBX **cannot depth-interleave per-poly with
the native effect prims** — it sorts wholesale in front of or behind the effect layer. Effects meant to
wrap the creature (fire in front / swirl behind) are the failure case. **This is the fidelity ceiling that
only the native slot (T2) removes** (its polys enter the same ordering table as the effects).

### 1.6 The clean camera test (offline, zero playtest)

Extend the probe per FORMAT §5. Then, per frame, project **one controlled world point** through BOTH the
logged managed `VIEW·PROJ` and the native `PSXCAM` (M + OFX/OFY/H). **Predicted:** screen delta ≈ 0
(sub-pixel modulo fp12 + widescreen aspect). This isolates the MAPPING from the datum/instant confounds
and settles §1.2/§1.4 without a single in-game judgment.

---

## 2. THE CLOCK

### 2.1 Native motion (T2 native slot) — locked by construction (PROVEN)

FORMAT §2.4: one sample per rendered frame, advance `frame+1`, no interpolation. `Hi_DrawSummonModel`
increments the native motion-frame counter `rec+0x54` per Draw (`0x17888`); loop-vs-hold-last is the
op-25 `loopFlag` **Draw argument**, not clip data. Draws happen inside `SFX_Update` ticks ⇒ the creature's
motion is **welded to the native tick**. WAIT/hold beats (loader-script `0x01 WAIT`): `SFX_Update` still
ticks; the creature Draw holds its last frame. **No managed clock is involved — perfect sync, inherent.**

### 2.2 FileList `Animations` clip (T1b) — advances on `SFX.frameIndex` (PROVEN)

`SFXDataMesh.JSON.Render(frame)` (`SFXDataMesh.cs:801-858`) is a **manual, frame-driven sampler**, not
Unity `Time`:

```csharp
clipState = anim[animName]; anim.Play(animName);
clipState.speed = 0f;                                   // frozen
clipState.time  = clipState.length * animFrame / animMaxFrame[animIndex];
anim.Sample();                                          // pose exactly at animFrame
```

`animFrame` is computed from the `frame` argument (`:841-851`). `frame` is `run.frame` (SFXData driver:
`sfx.mesh.Render(run.frame, run)`, `SFXData.cs:120`), and in the summon path `Runtime.Render`'s
`Load(frame)` synchronizes `SFX.frameIndex` to it (`:582`). **⇒ the FBX clip advances on the native
`SFX.frameIndex` (~15 fps native tick)** and holds correctly through WAIT beats (the frame index does not
outrun the native sim). The clock is unified with the effects and camera. (Speed-scaled sub-frames via the
`Animations[].Speed` token are honored inside the same `frame` domain.)

**BUT (T1b's animation gap, not a clock gap):** this only plays the FBX's **own authored clip**. It does
**not** inherit the *creature's real motion*. A rigid FBX with a canned idle is the overlay's failure in a
new costume. Faithful animation on the managed path REQUIRES driving the mesh from the native bones (§2.3).

### 2.3 Hybrid (native bones → managed mesh) — synced because it IS the native motion (PLAUSIBLE build, PROVEN read path)

Read `Hi_GetSummonBoneMatrix(slot=0, bone, out)` (real body `@0x18630`, A5 §6) **per native tick** →
the creature's actual per-bone WORLD matrix (32-byte PSX MATRIX, `data+0x38` array, stride `0x20`) → pose
our mesh's corresponding bone. Sampled on the native tick, it is the native motion **by definition** — the
sync question disappears. **This is the faithful animation the overlay never had.**

**Two build caveats bound the hybrid (delivery-side, T1/T2's problem but they gate T4's ceiling):**
* The existing FileList path **cannot inject per-bone matrices** — `JSON.Render` only sets a whole-object
  `transform.position/eulerAngles/localScale` and plays a named clip. Driving a skeleton needs a **new
  managed renderer** that writes a `SkinnedMeshRenderer`'s bone `Transform`s each frame from the native
  matrices (+ a PSX-world→Unity-world conversion analogous to `PsxMatrix2UnityMatrix`).
* Our mesh must be **rigged to the creature's skeleton** (≈93 bones for Bahamut) to consume its bone
  matrices. A model with an unrelated skeleton can only be driven at a coarse level (root + a few bones)
  and loses the real deformation. Retargeting is the honest cost.

---

## 3. THE EFFECTS

### 3.1 Effects play regardless of the creature model — CONFIRMED for a full-body swap (PROVEN)

The swirl/beam/fire-column are separate `SFXMesh` command-buffer entries (keyed by `_key`) and separate
`EFFARR` eff-slots (32-slot array `@0x220230`, adjacent to the 1-slot summon array `@0x220830`). The
summon hide mask (`SummonData+0x20`) is **summon-model-only**: `Hi_DrawEffModel` and friends contain **zero
references** to it (D4 §1.3, `V-M1-11`), and the mesh loop re-reads it per mesh (`0x17910-0x17919`) to skip
**only** the creature's own body polys. So `mask = (1<<meshCount)-1` (`0x3` for Bahamut's 2 meshes) is a
guaranteed, emission-free **full-body hide that leaves every effect rendering** — exactly the Thomas-swap
need. The HideMeshes work already demonstrated effect independence; this confirms it for the total hide.

### 3.2 Bone-parented effects follow the SKELETON, and it keeps computing under a hidden body (PROVEN)

Many eff-slots are **hard-parented to a creature bone**: `Hi_DrawEffModelByBone` copies a summon **bone's
world matrix** into the eff model's root verbatim (`0x1691b-0x16928`, FORMAT §1.5). Hiding the body meshes
does **not** stop bone computation — `build_world_matrices@0x7820` rebuilds `data+0x38[k]` every Draw
irrespective of the mask (the mask is consumed later, only at poly emission). ⇒ **in the HYBRID (hide
native body, keep effects, overlay our mesh), the bone-parented effects stay correctly placed by the
native skeleton** while our mesh renders over them.

### 3.3 For a full model SWAP (T2), bone INDEX conformance is load-bearing

If our model **replaces** id-4/id-5 (W5), the bone-parented effects now read **our** bone world matrices,
and the effect program queries specific bones **by number** (ops 149/164/162 `Hi_GetSummonBone*`). A rig
whose bone **indices** don't match the donor's scatters every parented prop. FORMAT §4.3 W5 already lists
this among the silent-failure conformance constraints; it is the effects' expression of it.

---

## 4. THE FIDELITY CEILING OF EACH PATH (the slice's verdict)

| axis | **T2 native slot** (W5) | **T1b FileList FBX** (managed perspective) | **HYBRID** (managed mesh posed by native bones) |
|---|---|---|---|
| **camera** (cuts/dolly/zoom) | EXACT — GTE draws it | **FAITHFUL** — Camera.main == native (§1.2) | **FAITHFUL** — same as T1b |
| **animation** (the real motion) | EXACT — native motion clip | **NONE** inherited — only the FBX's own clip (§2.2) | **FAITHFUL** — native bones drive the mesh (§2.3) |
| **clock / WAIT-hold sync** | EXACT — welded to tick | UNIFIED on `SFX.frameIndex` (§2.2) | UNIFIED — sampled on the native tick |
| **effects present** | yes, native | yes, independent (§3.1) | yes, independent + skeleton-placed (§3.2) |
| **effect DEPTH interleave** | EXACT — shared OT | **BROKEN** — screen-space vs perspective (§1.5) | **BROKEN** — same regime split |
| **bone-parented props** | follow OUR bones (index conformance, §3.3) | follow the (unused) native skeleton — desynced from the FBX | follow the native skeleton = correct vs our posed mesh |
| **effort** | HIGH (geometry emitter + R5 + rig conformance) | LOW (existing path) | MED (new bone-injection renderer + rig-to-donor-skeleton) |
| **provenance** | build-time transform of the user's install (verbatim-fork class) | clean (our FBX) | reads native bone matrices = pose data (sanctioned, like the camera track) |

**Reading of the table:**

* **The overlay's specific failure (a rigid billboard that couldn't read as a creature flying/banking/
  shrinking/rolling) is fixed by EITHER inheriting the camera (dissolves the fly-by/zoom problem) AND
  inheriting the animation (dissolves the banking/rolling problem).** T1b fixes the camera but not the
  animation; the **HYBRID fixes both** and is the leading candidate.
* **The HYBRID's only residual is the effect DEPTH regime** (§1.5) — a wholesale front/behind sort of the
  managed mesh against the screen-space effect prims. For a summon whose effects mostly frame the creature
  (a plunge camera on the creature with fore/background bursts) this may read acceptably; for effects that
  physically wrap the body it will not.
* **The native slot (T2) is the true ceiling** — the only path with per-poly depth-correct effects — but it
  pays the full W5 cost (geometry emitter, the R5 program read, and rig conformance to the donor skeleton),
  and its bone-parented props impose the **same** skeleton-conformance the hybrid needs anyway.

**Recommendation for T4's concern (lockstep):** the HYBRID is the highest-fidelity path that does not
require the W5 geometry/MIPS stack. Its camera + animation + clock lockstep are all either proven or
proven-mechanism; its single open risk is depth-compositing, which is **measurable before any playtest** —
render the hybrid against a stock cast and inspect whether any effect must pass *through* the creature
volume. If none does, the hybrid reaches the overlay's unreachable bar. If some do, that specific summon
needs the native slot.

**The two zero-playtest gates to run first (both offline, on the extended probe):**
1. **Camera-mapping gate (§1.6):** logged managed `VIEW·PROJ` vs native `PSXCAM` on one control point → ≈0.
2. **Instant-phase gate (§1.4):** logged managed `VIEW` == native `PSXCAM` M **per frame** → no live phase.
Passing both converts §1's "faithful by construction" from analysis into measurement.

---

## 5. PROVENANCE

Read-only static analysis of the user's own DLL (cited `fn@rva`) + open-source `Assembly-CSharp` cites +
structural counts from the existing `C:/gd/SCRATCH/summon-format/` extraction. No stock geometry,
animation payload, texture, or `ef###.bytes` was read into or quoted in this report. Reading
`Hi_GetSummonBoneMatrix` per-frame to **drive our own mesh** is pose/choreography data (the sanctioned
class, like the camera track). Dumping `bones[1..N-1]` across a cast as a redistributable animation asset
stays BLOCKED. No DLL is modified or shipped.
