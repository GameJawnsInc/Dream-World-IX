# T1 — THE BONE-DRIVEN TRANSPLANT (can our model wear the dragon's real skeleton?)

**The question (verbatim from the round brief):** can we render OUR OWN skinned model **posed by the
creature's REAL per-frame skeleton**, so it inherits the dragon's actual animation + camera — instead of
compositing a hand-choreographed rigid billboard (the FLIGHT overlay dead end)?

**Verdict up front:** **YES, mechanically — and the leading design is not the one the brief nominated.**
The single richest read is not "bake the dragon's 93-bone animation onto our model as a clip"; it is
**drive our model's bones LIVE, each frame, from the 93 already-composed WORLD matrices the native
renderer just built at `SummonData+0x38`.** That one read carries the articulation *and* the root flight
*and* the 0.02→3.0 authored scale sweep, in perfect lockstep, and it ships zero stock bytes. The
irreducible cost — the same for every variant below — is that **our mesh must be skinned to a rig that
reproduces the dragon's rest pose and node correspondence** (the "same-skeleton" retarget). Provenance:
reading the live per-frame bone matrices to *drive our mesh* is the sanctioned choreography class (like
the camera track); baking the dragon's animation to a redistributable clip is stock content and is
SCRATCH-only.

All RVAs image-base-relative (x64 `ImageBase 0x180000000`). C# cites relative to
`C:/gd/FFIX/Memoria/Assembly-CSharp/`. Confidence tags: **PROVEN** (statically/independently verified this
slice), **PLAUSIBLE** (source-traced or one-step-inferred, not yet run), **SPECULATIVE** (reasoned, unverified).

---

## 1. THE SOURCE SKELETON — layout, count, hierarchy, world-vs-local

### 1.1 The per-bone world-matrix array — PROVEN

`SummonData+0x38` is a pointer to an array of **32-byte PSX GTE MATRIX** records, **stride `0x20`**, one
per node, **93 for `ef227`/Bahamut** (`u8[model+0x02]`; M5 §3/§4). Record format (both arches):

```c
struct PSXMATRIX {          // 32 B
/*+0x00*/ s16 m[3][3];      // 3x3 rotation, fixed-point /4096  (1.0 == 0x1000)
/*+0x12*/ s16 pad;
/*+0x14*/ s32 t[3];         // translation X,Y,Z, GTE world units
};
```
Read one bone with `Hi_GetSummonBoneMatrix(idx, boneIdx, out)` real body **@0x18630** (B1 §2), or —
better for a per-frame loop — dereference `*(MATRIX*)(SummonData+0x38)` and index `k*0x20` directly
(no call into the plugin). The s53 probe already does exactly this read for `bones[0]`
(`SfxMeshProbe.cs:636-651`, `DataBonesOff=0x38`, `MatrixStride=0x20`).

**This is not the anchor the FLIGHT overlay was built on.** The s52 log's `+0x40` is only the *input*
anchor (`R·S` — the scale-carrying draw anchor, M5 §8 Finding B); the array at `+0x38` is the *output*
the GTE actually consumed.

### 1.2 The matrices are WORLD-space and already COMPOSED — PROVEN (re-verified this slice)

I disassembled the shared node builder `0x7820` independently this slice and it settles the A1-vs-A2
contradiction in A1's favour:

```
0x7838  mov r14,[rcx+0x10]        ; r14 = DATA+0x10  (motion-clip ptr)
0x7842  mov [rcx+0x38],r8         ; DATA+0x38  <-  nodeBuf   (set ONCE per Draw, not per node)
0x7846  test r14,r14 ; jne 0x7a20 ; motion?  -> branch M (animated)
0x784f  mov rax,[rcx+0x30] ; je 0x797a ; no parent? -> branch R (free rigid)
```
* **Branch R** (`0x797a-0x7a10`, disassembled this slice): copies `DATA+0x40`'s 3×3 into `bones[0]`
  (the array at `[rsi+0x38]`) **with columns 1,2 negated** (`neg cx` at `+0x02/+0x04/+0x08/+0x0a/+0x0e/+0x10`)
  and `DATA+0x54/58/5c` translation verbatim into `bones[0]+0x14/18/1c`. i.e. `bones[0] = DATA+0x40`
  with the PSX `diag(1,-1,-1)` handedness flip. This proves the array entries ARE world matrices (the
  root entry equals the world draw anchor), not bone-local ones.
* **Branch M** (every real summon frame — a motion is bound): `bones[0].R = R_root · clipRotation[0](frame)`,
  `bones[0].t = R_root · rootTranslation(frame) + T_root` (M5 §5, GTE `RotTrans 0x3d60` verifiably
  ADD-ing `T` at `0x3dc5`/`0x3df2`). Children chain: `world.R[k] = world.R[parent] · local.R[k]`,
  `world.t[k] = world.R[parent]·(0,0,length[k]) + world.t[parent]` (M5 §4).

⇒ **every entry in `SummonData+0x38` is that node's WORLD transform for this frame, fully composed:
per-bone animation ∘ root TRS ∘ authored scale.** FORMAT.md §1.2 corroborates from the draw side: the
plugin composes `bones[k]` with the view matrix `M` and *does not* re-apply its own transform — which is
only consistent if `bones[k]` is already world.

### 1.3 The hierarchy — PROVEN, and it lives in the MODEL, not the clip

The skeleton is a 4-byte-per-node table at `u32[model+0x0c]` (M5 §4):
```c
struct Node { s16 length; u8 unused; u8 parentIndex; };   // local translation is HARD-CODED (0,0,length)
```
`nodeCount = u8[model+0x02]` (93 for Bahamut). **A parent's index is strictly lower than its child's**
(the hierarchy pass walks in index order with no sort — a hard re-import constraint). A bone's only
geometric freedom is a scalar length along local Z; there are **no arbitrary per-bone offsets**.

**Consequence for the transplant:** we do not have to reconstruct the hierarchy at runtime to drive our
mesh in world space (§2), but to *author* a conformant rig we must respect parent-index ordering and the
"length-along-Z, root-only-translation" convention.

### 1.4 What is NOT recoverable statically — PROVEN

The array VALUES are runtime `.bss`/heap scratch (zero on disk); only the LAYOUT + ACCESS PATH are
static. The matrices exist only while a cast is live — which is exactly why the delivery reads them
per-frame (§2a) rather than baking them from the file. (The motion *clip* IS on disk and IS
offline-decodable — §2b — but the clip is only the per-bone LOCAL rotation; the world result additionally
needs the runtime `(rot,pos,scale)` draw args fed by the effect program.)

---

## 2. THE DELIVERY — how our model consumes it

### 2.0 What the existing model pillar exposes — PROVEN (read from source)

The proven loose-FBX renderer is `SFXDataMesh.JSON` → `ModelFactory.CreateModel(path,…)`
(`ModelFactory.cs:50`) → a Unity `GameObject`. Per frame, `JSON.Render(frame)` sets **only the
whole-model transform** and plays an **AnimationClip**:
```csharp
tok.unityObject.transform.position   = tok.movement.GetPosition(frame,…);   // SFXDataMesh.cs:831
tok.unityObject.transform.eulerAngles= tok.rotation.GetPosition(frame,…);   // :832
tok.unityObject.transform.localScale = tok.scaling.GetPosition(frame,…);    // :833
…GetComponent<Animation>().Play(animName); clipState.time = …; …Sample();   // :854-858
```
**It exposes NO settable per-bone/joint matrix set** — bone poses come only from a Unity `AnimationClip`
sampled at a time. A grep of the whole `Battle/SFX/` tree finds **zero** references to
`SkinnedMeshRenderer.bones`/`bindposes`. So the two delivery options fork here:

### 2.a — LIVE per-frame WORLD-matrix bone drive (**the leading candidate**)

**Mechanism.** In a `memoria-patches` hook co-located with the s53 read (inside `Runtime.Render`, AFTER
`SFX_LateUpdate`/`SFXRender.Update`, so `DATA+0x38` holds this frame's matrices — `SFXDataMesh.cs:641-659`):

1. Once: load our FBX via `ModelFactory.CreateModel` (or the FileList route), grab its
   `SkinnedMeshRenderer smr`, disable its `Animation` component. `smr.bones` is the bone `Transform[]`.
2. Per frame: `IntPtr bones = ReadIntPtr(sData + 0x38)`; for `k` in `0..92` read the 32-byte matrix at
   `bones + k*0x20`, convert PSX→Unity (§2.a.1), and write **absolute world pose** onto `smr.bones[k]`:
   `smr.bones[k].position = uPos_k; smr.bones[k].rotation = uRot_k;` (optionally scale).
3. Unity re-skins `smr` from the driven bones and renders it through `Camera.main` — which carries the
   **native** VIEW/PROJ the plugin installs each frame (§2.a.2).
4. Hide the native creature body: assert the native total-hide mask
   `Marshal.WriteInt32(sData+0x20, (1<<meshCount)-1)` = `0x3` for Bahamut (FORMAT §3.4 — emission-free,
   hash-independent full body hide) each frame, OR use the managed `HideMeshes=` body-key split. The
   native eff-model props (beams/rings/fire column) keep rendering.

**Why this is the strongest option — PROVEN reasoning:**
* **One read = the whole pose.** The `+0x38` matrices already fold articulation + root flight + the
  0.02→3.0 scale (§1.2). No offline motion decode, no separate root/scale feed, nothing to keep in sync
  by hand. It is *the exact pose the native renderer used this frame*.
* **Perfect lockstep by construction** — it reads the matrices the plugin wrote this same native tick.
* **No hierarchy dependency at drive time.** We set each bone's WORLD transform absolutely, so our
  model's own bone-parenting is overwritten every frame; only *correspondence* (bone `k` ↔ node `k`) and
  *bind pose* matter (§3).
* **Provenance-clean:** reads runtime pose to drive our own mesh (the camera-track class) and ships no
  stock content.

**Costs / risks:**
* **New engine code, not just a probe.** This *renders content* (loads + drives our FBX), so it is a
  memoria-patches FEATURE (an owner go/no-go class, one step past the s52/s53 passive read), not a probe
  extension. ~60-120 lines: load/cache the model, the per-frame bone loop, the hide-mask write.
* **The retarget (§3)** — the irreducible cost, shared with 2.b.
* **PSX→Unity calibration** (§2.a.1) — one empirical scale + a fixed sign map; measurable, not guessed.
* **Camera-projection fidelity** (§2.a.2) — PLAUSIBLE, the one residual to prove in-game.

#### 2.a.1 The PSX→Unity conversion — PLAUSIBLE, with a built-in validator
Per bone: rotation = the `s16` 3×3 ÷ 4096 (a MODEL/local→world basis — do **not** run it through
`PsxMatrix2UnityMatrix`, which is for a VIEW matrix, B1 §5); translation = the `s32` triple. Map into the
same Unity world space `Camera.main` uses via the VIEW's own column convention
`unityPos ≈ (tx, -ty, -tz) / scale` and `unityRot` = the 3×3 with columns 1,2 negated (the `diag(1,-1,-1)`
flip the plugin itself applies, `0x797a`). **The scale factor and exact sign are calibrated ONCE** against
the s53 `PRIM` screen AABB / `BONES` AABB (the built-in faithfulness validator, FORMAT §5 step 5) — a
zero-free-parameter check, not a search. **The dragon's authored scale sweep (0.02→3.0) is already inside
the `+0x38` matrices' columns**, so it is reproduced automatically; this is the FLIGHT-killing term the
overlay's `root_reproject.py` silently discarded (M5 §8 Finding B).

#### 2.a.2 Camera inheritance — PLAUSIBLE (rung-7 makes it likely)
During `SFX_PLUGIN` playback the plugin overrides `camera.worldToCameraMatrix` **and**
`camera.projectionMatrix` directly every frame (`SFX.cs:1603-1604`, per the s50 note in
`SfxMeshProbe.LogCamera`). A `SkinnedMeshRenderer` in the scene renders through `Camera.main` with those
overridden matrices ⇒ **our puppet inherits the native cinematic camera for free.** Rung 7 already proved
a Unity FBX composites INTO a live native battle effect and is visible; the open point is whether it
inherits the *summon's* exact per-frame VIEW/PROJ (the cinematic camera with its 15 hard cuts and 47°→24°
push-in) rather than the default battle camera — and whether the plugin's own restore of
`worldToCameraMatrix` (`SFXDataMesh.cs:636/678`) races the puppet's render pass. Both are testable in one
cast. **This is the crux fidelity residual — but note it is strictly weaker than the overlay's problem:**
because we HIDE the native body and show only our puppet, we need our puppet merely at the creature's
world coords in Camera.main's frame, NOT pixel-registered onto the native GTE output. The native creature
draws through the plugin's own software GTE (`M` + OFX/OFY/H, FORMAT §1.2); our puppet draws through
Camera.main's VIEW/PROJ — two re-derivations of the SAME PSX camera track. Placing our puppet at the
creature's decoded world position reproduces the shot as long as those derivations agree (PsxCamera's job).

### 2.b — BAKE an offline FBX ANIMATION CLIP (the reuse-the-proven-route fallback)

**Mechanism.** Offline, decode the motion clip (fully decoded, M5 §2: 12-bit coarse+fine Euler, root
tracks) → per-node LOCAL Euler keyframes on our rig → a Unity `AnimationClip` (or an FF9 FIELD anim,
mint band 60000-65535). Ship it through the proven FileList/`SFXDataMesh.JSON` route (rung 7): the
`Animations` list plays via `Animation.Sample`, `clipState.time = length * animFrame/animMaxFrame` where
`animFrame` derives from the `frame` argument (`SFXDataMesh.cs:836-858`).

**Does the FileList playback sync to the native tick? — PLAUSIBLE-good.** `JSON.Render(frame)`'s `frame`
is the shared `SFXData` render frame (the same clock the native `Runtime.Render` advances via
`SFX.frameIndex`). A `[model]` token added to the effect's managed `.seq` renders alongside the native
effect, same frame, so the clip stays frame-locked to the cinematic. The native tick can advance multiple
`SFX_Update` per managed frame (FORMAT §1.3), but the camera has the same property, so puppet and camera
stay consistent *relative to each other*.

**Why it does NOT dominate 2.a — PROVEN reasoning:**
* **It captures only the ARTICULATION.** The baked local rotations reproduce the per-bone motion, but the
  **root flight (translation) and the scale sweep come from the runtime draw args** `(rot,pos,scale)` that
  the effect program (opaque MIPS, id-3) feeds `Hi_DrawSummonModel`. For a NATIVE cast these are **not
  offline-decodable**, so 2.b must ALSO read them at runtime (the ROOT probe, `DATA+0x40` = `R·S` +
  `DATA+0x54`) and drive the whole-model `Movement/Rotation/Scaling` — re-introducing exactly the staging
  term FLIGHT never had. Net: 2.b = offline articulation clip **+** a runtime root/scale feed = strictly
  more moving parts than 2.a's single world-matrix read, for LESS coverage.
* Sync between the *articulation* clip and the *root* feed becomes a second thing to keep aligned.

**Where 2.b wins:** it reuses the in-game-proven rung-7 route with **zero new per-frame native machinery**,
and the motion decoder is committable code. A sensible **hybrid** is "2.b's articulation clip + 2.a's live
`DATA+0x38`-based root/scale" — but if you are already reading `+0x38` live, reading all 93 (2.a) is
simpler and more faithful than reading 1 + playing a clip.

### 2.c — delivery scorecard

| axis | 2.a live world-matrix drive | 2.b baked clip (+ runtime root) |
|---|---|---|
| captures articulation | ✅ (from `+0x38`) | ✅ (offline decode) |
| captures root flight | ✅ (same read) | ⚠ runtime feed required |
| captures scale sweep | ✅ (same read) | ⚠ runtime feed required |
| sync to native tick | ✅ by construction | ✅ shared `SFXData` frame (PLAUSIBLE) |
| new per-frame engine code | new memoria-patches FEATURE | reuses proven rung-7 route + a root feed |
| offline motion decoder needed | no | yes (committable) |
| exposes settable bones today | no — must add `smr.bones` writes | no — clip only, which is fine |
| provenance | clean (drive-only) | clip is stock content → SCRATCH-only |

---

## 3. RETARGETING — mapping the dragon's 93 nodes onto our model

**The problem:** our model (Thomas humanoid, or a from-scratch creature) has a DIFFERENT skeleton than the
93-node dragon. Both delivery options need our mesh posed by the dragon's per-node transforms, so both
need a correspondence.

### 3.1 The minimum viable retarget = SAME-SKELETON (author our mesh ON the dragon's rig) — PLAUSIBLE
The kit already emits skinned FBX in exactly the shape this needs (`models/fbx_skin.py`): one bone
`Model` per bone, **NAMED `bone{NNN}` where the trailing digits ARE the FF9 node number**, and the
importer **recomputes bind poses from each bone's rest transform**. So the MVP is:

1. A tool (committable) reads the USER's own `ef227` and emits a **rig reference**: 93 bones in node
   order, parent indices, bone lengths (`Node.length` → local `(0,0,length)`), rest pose. *(The rig is
   stock-derived geometry → the emitted rig stays LOCAL under SCRATCH; only the tool ships.)*
2. The user authors/skins THEIR mesh onto that rig in Blender (bones `bone000..bone092`), weights their
   choosing. This is the one creative cost, and it is the natural cost of "wear the dragon's animation."
3. Drive is then **1:1 by node index** (`smr.bones[k]` ↔ node `k`) — no cross-rig math. For 2.a the world
   matrices land directly; for 2.b the clip's per-node keys bind by bone name.

**Why same-skeleton, not true retarget:** driving `smr.bones[k]` to the dragon's world matrix skins our
vertices as `dragonWorld[k] · ourBindpose[k] · vertex`. For that to be correct, `ourBindpose[k]` must
invert the dragon's REST pose for node `k` — i.e. our mesh must have been bound in the dragon's rest pose.
Authoring on the dragon rig gives that automatically. Fidelity is then exact (PROVEN mechanically; the
in-game look is PLAUSIBLE pending the camera residual §2.a.2). Best fit when our creature's topology
suits a long-necked flyer (another dragon/quadruped/serpent).

### 3.2 True cross-rig retarget (dragon → arbitrary humanoid) — SPECULATIVE, HIGH effort
Mapping 93 dragon nodes onto, say, a ~30-bone humanoid needs: (a) semantic node labels (which node is
neck/wing/tail — the bone-label tooling, `project-ff9-bone-semantic-labels`, can carry these), (b) a
bone-name/offset mapping, (c) a Blender retarget (Rokoko/Auto-Rig-Pro-style) with per-bone offset
correction. It is LOSSY for dissimilar topologies (a dragon has no humanoid correspondence) and is the
FLIGHT overlay's aesthetic problem in a new place. **Not recommended as the MVP.**

### 3.3 Subset drive — PLAUSIBLE partial
Drive only a labelled subset (root + spine + head) from the corresponding dragon nodes and leave the rest
to a Unity idle. Lower fidelity, useful only if same-skeleton authoring is infeasible.

---

## 4. RECOMMENDATION (T1 slice)

1. **Build 2.a (live `DATA+0x38` world-matrix bone drive) as the primary path.** It is the faithful
   transplant the overlay could never be: our mesh, the dragon's real per-frame pose (articulation + root
   + scale), the native camera. One read, perfect sync, zero stock content shipped.
2. **Ship the SAME-SKELETON retarget tool (§3.1):** `summon-rig-ref` reads the user's own `ef227` and
   emits a local 93-bone rig reference (bones named by node number) for the user to skin their mesh onto.
3. **Keep 2.b (the offline motion decoder, M5 §2) as a committable TOOL** — it is independently valuable
   (R3 in the roadmap) and enables the hybrid, but do not make it the delivery vehicle: it under-captures
   the flight for a native cast.
4. **Prove the camera residual (§2.a.2) in ONE cast** before investing in polish: does a
   `SkinnedMeshRenderer` in the scene inherit the summon's per-frame VIEW/PROJ, or the default battle
   camera? This is the last unknown between "mechanically works" and "reads as the creature."

**Sequencing dependency:** 2.a needs the s53 read (done, `SfxMeshProbe.LogModels` proves the `+0x38`
access is live and safe) → the calibration constant (§2.a.1, one instrumented cast, the validator is
built in) → the retarget rig (§3.1) → the memoria-patches drive feature. None of it needs the id-3 MIPS
decode.

---

## 5. FALSIFIABLE PREDICTIONS / WHAT WOULD SINK THIS

* **P1 (PROVEN false-if):** if a live cast shows `bones[0]` at `DATA+0x38` is **zero or static** while the
  creature visibly animates, §1.2 is wrong for this build. (Contra: node builder writes it every Draw,
  `0x7842`; s53 already reads it.)
* **P2 (the calibration):** projecting the driven `bones[0].t` through the s53 `PSXCAM` `M`+OFX/OFY/H (or
  Camera.main's VIEW/PROJ) lands inside the creature's own `PRIM` AABB on framed frames (FORMAT §5). If it
  does, the PSX→Unity map is proven; if not, the raw `PsxCtx[+0x14]` tamper column says whether the effect
  re-pointed the view — a bounded next question, not a guess.
* **P3 (camera inheritance):** a `SkinnedMeshRenderer` composited into the effect renders through the
  summon's per-frame VIEW/PROJ (not the static battle camera). Rung 7 makes this LIKELY; unproven.
  **If P3 fails**, 2.a degrades to "our puppet at the right world pose but the wrong projection" — at
  which point we drive Camera.main from the decoded native camera track (W-CAM territory) or render the
  puppet through an explicit matrix.
* **P4 (retarget topology):** same-skeleton authoring is only pleasant for creatures whose silhouette
  suits a 93-node dragon. A humanoid Thomas on a dragon rig is SPECULATIVE and may look wrong regardless
  of correct posing — a design (not engine) risk to flag to the user early.

---

## 6. PROVENANCE (this slice)

* Native claims are read-only static analysis of the user's own installed `FF9SpecialEffectPlugin.dll`
  (x64), cited `fn@rva : ins@rva`. **The node builder root branch was independently re-disassembled this
  slice** (`0x7820-0x7a10`) and matches B1/M5; no new stock bytes were read from any container.
* **No DLL patched or redistributed, and none will be.** 2.a's drive feature is a memoria-patches
  managed change performing PASSIVE reads of the plugin's already-computed runtime pose (the camera-track
  class) — it writes no shippable asset bytes and calls no plugin export.
* **Reading `bones[0..92]` to DRIVE our own mesh live is the sanctioned choreography class.** BAKING those
  matrices to a redistributable clip/rig (2.b's output, §3.1's rig reference) is derived stock content and
  stays LOCAL under `C:/gd/SCRATCH/summon-transplant/`, never committed, never shipped — exactly the
  battle-import / verbatim-fork precedent. The DELIVERABLE is the pipeline + tools; the user runs them on
  their own install.
* Committable this slice: this report, and the (design-only) tool specs. No `ef###.bytes`, geometry,
  animation payload, or matrix VALUES were written anywhere.
