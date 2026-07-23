# T3 — THE BLENDER ROUND-TRIP (decode a stock summon → armature + skinned mesh + baked animation → Blender → back)

**Slice T3 of the transplant round.** The user's second explicit ask, verbatim: *"and maybe at some point
export them into Blender."* This document designs the pipeline that turns a **locally-decoded** stock summon
creature into a standard interchange file (glTF `.glb`) with an **ARMATURE + skinned mesh + baked animation
clips**, openable in Blender, where the user RETARGETS their own model onto the dragon's rig+animation, then
exports it back for the game.

It builds on the already-decoded formats (M4 geometry, M5 motion, FORMAT.md §2.3/§2.4, `ef_container.py`) and
on the project's **proven model pillar** (`ff9mapkit/models/`, the Blender add-on) — it does not re-decode
anything. Every claim is marked **PROVEN / PLAUSIBLE / SPECULATIVE** and cited `fn@rva` / `file:line`.

RVAs are image-relative for the user's own `FF9SpecialEffectPlugin.dll` (x64 `ImageBase 0x180000000`). C#
cites are relative to `C:/gd/FFIX/Memoria/Assembly-CSharp/`. Kit cites are relative to
`ff9mapkit/ff9mapkit/`.

---

## 0. HEADLINE — three results

1. **The decode already yields everything an armature + skinned mesh + baked animation needs, and it maps
   almost 1:1 onto the kit's existing Model struct.** The run-length rigid skinning (each vertex hard-bound to
   exactly ONE bone) is the *cleanest possible* skin: it drops straight into the kit's per-vertex
   `[(boneNum, weight)]` weight format as `[(b, 1.0)]`. The bone-link table is a standard parent+length
   skeleton. The only field a full decode is still missing is **the exact angle→matrix Euler composition** of
   the motion clip — one bounded read of three DLL functions (§2.4), and its correctness is **free to
   validate** against the s52/s53 probe's already-logged composed bone-0 matrix.

2. **The exporter is "`model-gltf` for summon creatures."** It reuses the kit's glTF emission
   (`models/gltf.py`), buffer/writer (`models/_gltf_io.py`), and coordinate helpers wholesale; the ONLY new
   code is (a) a motion-clip decoder and (b) an adapter that builds the kit Model struct from a decoded
   `ef###.bytes` instead of from a p0data4 prefab. Output = **the exact same `.glb` the Blender add-on's
   Import Model already opens** (`blender/ff9mapkit_blender/model_ops.py:22`).

3. **The natural return-trip endpoint is the FileList FBX route (T1b, managed) — and it is already proven
   in-game (rung 7).** Because Unity `AnimationClip`s bind curves **by bone hierarchy PATH**, a user who
   retargets their mesh onto the dragon's `bone000..bone092` armature gets the dragon's baked clips to bind to
   their mesh for free. The managed lane supplies the skeletal animation; the **donor hybrid** supplies the
   native camera + staging (§3). Native injection (T2/W5) is the stock-grade endpoint but is HIGH effort and
   deferred.

**The honest scope line, stated up front so no playtest is wasted on it:** the motion CLIP is the **skeletal**
layer only (wing-flap, body-flex, the small ≤246-unit root drift — M5 §5). The big **staging** (the fly-down,
the 73k-unit fly-by, the 0.02×→3.0× perspective-scale — M5 §8 Finding C) is the **anchor** `(rot,pos,scale)`
the `.seq`/MIPS program hands `Hi_DrawSummonModel` every frame, which is **NOT in the clip**. A retargeted FBX
playing the baked clip alone will flap and bend exactly like the dragon but will not fly across the screen —
that trajectory is a separate layer (the donor hybrid, or authored `.sfxmodel` Movement curves; §3.4). Selling
the baked clip as "the whole cinematic" is the T3 version of the trap this project keeps hitting.

---

## 1. WHAT A FULL DECODE YIELDS — and is it enough for an armature + skinned mesh + baked animation?

**Yes, end to end.** Confirmed live this slice by running the committed parser on the local blob (read-only,
structural only): `py ef_container.py C:/gd/SCRATCH/summon-format/ef227.bytes` →

```
GEOM: bones=93 meshes=2 verts=1439 faces=2416
  mesh0: verts=797 uv=4134 col=0 {'FT4': 39, 'FT3': 1326}
  mesh1: verts=642 uv=3197 col=0 {'FT4': 44, 'FT3': 1007}
MODEL IMAGE @0x63000: geom [0x63000..0x7579c) then texanim, then 8 motion clips
```

### 1.1 The armature (skeleton) — PROVEN sufficient (M4 §3, M5 §4)

| what Blender needs | what the format gives | source |
|---|---|---|
| bone count | `u8[geom+0x02]` = **93** | `ef_container.Geom.bone_count` |
| parent per bone | `BoneLink[b].parentBone` (u8), **parent index < child index** (no sort pass) | `ef_container.BoneLink.parent`; M5 §4 |
| bone local translation | **`(0, 0, length)`** — `BoneLink[b].length` (s16), the classic FF9 parent+length skeleton | M5 §4 (`0x7abf` zeros X/Y, `0x8282` writes Z) |
| bone local rest rotation | **not stored** — the rest pose is implicit; the clip supplies all rotation | M5 §4/§5 |

The missing rest rotation is a **choice, not a gap** (§2.3): bind against clip[0] frame 0 and the Blender rest
pose shows the dragon in a recognizable pose; bind against identity and the armature is a stick-figure that
every clip fully poses. Either is internally consistent.

### 1.2 The skinned mesh — PROVEN sufficient, and the skin is the cleanest possible (M4 §4/§5/§9)

* **Vertices**: `positions[]`, 8-byte `s16 x,y,z,w` (`w` unread), in **bone-LOCAL space** (fn 0x4eb0
  transforms each bone's run by that bone's matrix). `ef_container.vertices()`.
* **Faces**: eight `POLY_*` buckets; **every stock creature uses only FT4 (textured quad) + FT3 (textured
  tri)** (M4 §2.3). `ef_container.iter_primitives()` yields per-face `v`/`uv`/`part`/`flag`. Quads → 2 tris
  at emit.
* **Skinning is RIGID + RUN-LENGTH** (M4 §4, PROVEN on 1041/1041 meshes: `maxVertexIndex == nVert-1`): vertex
  *n* belongs to the bone whose `vertsPerBone[]` run contains it — **exactly one bone, weight 1.0, no
  per-vertex index, no weights table**. `ef_container.bone_of_vertex(mesh)` returns the per-vertex bone list
  directly. This is a *gift*: the kit's Model struct wants `weights = [[(boneNum, w), ...]]` per vertex, and a
  rigid skin is simply `[[(b, 1.0)]]` — no weight normalization, no top-4 cap, no cluster ambiguity.
* **UVs**: `uv[]` pool, `u16` index → `(u8 u, u8 v)` texel pair (M4 §5.3). Per-face `part` byte → the
  `{tpage, clut}` VRAM binding. Enough to emit `TEXCOORD_0`; see §2.5 on normalization.
* **Materials/textures**: ≤6 parts, each `{tpage, clut}` (M4 §2). The pixels live in the id-4 texture pages
  (`64×128` 16bpp) + CLUT strip — a **separate decode** (M4 §7.5), deferrable to a placeholder for a retarget
  reference (§2.5).

### 1.3 The baked animation — PLAUSIBLE sufficient, one bounded unknown (M5 §2)

Each of the 8 clips decodes (M5, byte-validated to tile with 0 gaps / 0 overlaps) to, **per frame**:

* **per bone**: three 12-bit Euler angles (`coarse<<4 | fine`, 4096 units/turn) → a local rotation matrix.
* **root only (bone 0)**: three `s16` translation tracks (or constants) → the root local translation.

That is a complete baked clip: a rotation curve for every bone + a translation curve for the root. Cost is
tiny (M5 §3.1: Bahamut's entire 8-clip / 93-bone / 346-frame set is **82 KB**). The one thing not yet nailed
is the **exact Euler order + rotation sign** that turns the three angles into the matrix — §2.4.

**Verdict:** geometry + skeleton are PROVEN-sufficient today (`ef_container.py` already parses them). Motion is
PLAUSIBLE-sufficient pending the §2.4 read, which is bounded and self-validating.

---

## 2. THE EXPORTER — a committable "`summon-export`" tool

### 2.1 The reuse map (why this is small)

The kit **already** has the entire "Model struct → Blender-openable `.glb`" machinery, built for real
field/character models. The summon exporter is an **adapter** that produces the same Model struct from a
decoded container, plus a motion decoder. Concretely:

| stage | reuse verbatim | new code |
|---|---|---|
| container/geometry parse | `ef_container.py` (`parse_header`, `parse_model_package`, `creature_geom`, `iter_primitives`, `bone_of_vertex`) — **committable, validated 372/372** | — |
| motion decode | — | **`summons/motion.py`** (§2.4) — the one real new piece |
| build the Model struct | the struct SHAPE (`models/extract.read_model`'s output contract: `bones[]`, `meshes[]`, `materials[]`, `root_bone`, `textures{}`) | **`summons/build.py`** (§2.2/§2.3) — the adapter |
| glTF emission | `models/gltf.py`'s node/skin/mesh/material/animation emission + `models/_gltf_io.py` (`GltfBuffer`, `write_glb`) + coord helpers `_cpos`/`_cnrm`/`_cquat`/`_sign_continuous` | a thin `export_summon_gltf(model, clips, out)` that feeds **pre-decoded** clips instead of calling `_select_anim_keys` (which reads p0data5) |
| open in Blender | the add-on's **Import Model** (`model_ops.py:22`, `bpy.ops.import_scene.gltf`) — **unchanged** | — |

`gltf.export_gltf` (`models/gltf.py:160`) is 90% reusable but is coupled to `extract.read_model` (p0data4) and
`_select_anim_keys` (p0data5). The clean move is to **factor its emission body into `emit_model_gltf(model,
clips, buf, out)`** and have both `export_gltf` (real models) and `export_summon_gltf` (summons) call it. The
animation loop (`gltf.py:324-382`) already does exactly what we need — it walks `clip["bones"]` and emits
rotation/translation/scale channels keyed by bone number — so a summon clip in that same `{path: {"rot":
[(t,q)], "pos": [(t,p)]}}` shape (which `motion.py` produces) flows through **unchanged**.

### 2.2 Building the Model struct — bones + meshes (PROVEN math)

```python
# summons/build.py  (sketch)
import ef_container as efc   # promoted into the kit, or vendored

def summon_model_struct(blob):
    c  = efc.parse_header(blob)
    mp = efc.parse_model_package(blob, c.chunks[0])     # the id4+id5 creature package
    g  = efc.creature_geom(blob, mp)                    # 93 bones / 2 meshes
    bones = _bones_from_links(g)                        # §2.3
    world = _rest_world_matrices(bones)                 # §2.3 — chosen rest pose
    meshes, materials = [], []
    for mi, m in enumerate(g.meshes):
        bov = efc.bone_of_vertex(m)                     # per-vertex bone (run-length)
        verts = list(efc.vertices(blob, g, m))          # bone-LOCAL s16
        # LIFT each local vertex into the chosen rest world pose = the bind pose the skin references
        vbind = [ _affine(world[bov[i]], v[:3]) for i, v in enumerate(verts) ]
        weights = [ [(bov[i], 1.0)] for i in range(m.n_vert) ]   # rigid skin -> one bone, weight 1
        uvs, subs = _faces(blob, g, m, materials)       # FT4->2 tris, FT3->1 tri; §2.5
        meshes.append({"name": f"mesh{mi}", "verts": vbind, "normals": None,
                       "uvs": uvs, "submeshes": subs, "weights": weights, "parent": None})
    return {"geo": None, "geo_id": None, "type_int": None, "root_bone": "bone000",
            "bones": bones, "meshes": meshes, "materials": materials, "textures": _textures(blob, mp)}
```

Every piece above is either already in `ef_container.py` or is the elementary math in §2.3. `normals=None` is
fine — `emit_skinned_fbx` and `export_gltf` both handle no-normals (the vertex 4th word is not a usable normal
— M4 §7.4).

### 2.3 The bind-pose construction — the load-bearing math (PROVEN)

This is the one place to get exactly right; it is standard skinning, derived directly from the PSX pipeline
(M4 §4, M5 §4/§5). The renderer computes, per bone, a **world matrix** `W[b]` and draws
`vertex_world = W[b] · vertex_local`. The hierarchy (M5 §4, anchor dropped for an offline rig, i.e. `R_anchor
= I, T_anchor = 0`):

```
W[0].R = restRot[0]                                  # root: anchor=I so local == restRot[0]
W[0].t = restRootTranslation                         # 0 for a static rest
for k in 1..N-1 (index order — parent<child guaranteed):
    W[k].R = W[parent].R · restRot[k]                # restRot[k] = the chosen rest local rotation
    W[k].t = W[parent].R · (0,0,length[k]) + W[parent].t
```

Then the skin is fully determined:

* **bind-pose mesh vertex** `= W[b] · pool_vertex` (the vert lifted into world rest pose).
* **inverseBindMatrix[b]** `= inverse(W[b])` — glTF computes these from the node rest pose automatically
  (`export_gltf` at `gltf.py:190-206`); the FBX importer likewise **recomputes** bindposes from bone rest
  (M4/`fbx_skin.py:14`). So we only supply consistent node rest TRS + bind-space verts.
* **node rest TRS**: translation `(0,0,length)`, rotation `restRot[b]`, scale `1`.
* **animation channel** `node[b].rotation(t)` = the clip's absolute local rotation for bone b at frame t
  (the engine sets `local.R = clipRotation` directly — M5 §5), and `node[0].translation(t)` = the clip root
  translation. At the reference clip/frame the channel value equals the rest, so the bind is consistent.

**The rest-pose choice** (`restRot[b]`): use **clip[0], frame 0** so Blender's rest pose is a recognizable
dragon (the mesh appears in its authored frame-0 shape). Identity is also valid (stick-figure rest, every clip
fully poses). Either is self-consistent — the animation is *absolute* local rotation, independent of the rest
choice.

Why this is exact and not a guess: `W[b]·inv(W[b])·W_anim[b]·pool = W_anim[b]·pool`, i.e. posing the bound
mesh by any clip reproduces the renderer's `W_anim[b]·pool_vertex` byte-for-byte, because `W` is built by the
same hierarchy recurrence the DLL runs (M5 §4). **PROVEN** modulo §2.4.

### 2.4 The one genuinely-new decode: angle→matrix (PLAUSIBLE, bounded, free to validate)

The clip stores three 12-bit Euler angles per bone per frame (M5 §2.3, decode PROVEN). Turning them into the
local rotation matrix requires replicating the engine's three per-axis builders and their composition:

* `RotMatrix` fns `0x37a0` (a0), `0x3850` (a1), `0x3910` (a2), called in that order into an fp12 identity
  seed (M5 §2.3, cites `0x7d8a/0x7d9a/0x7daa`). **Read: which axis each builds (X/Y/Z), the sin/cos sign
  convention, and whether the product is `Ra0·Ra1·Ra2` or the reverse.** This is ≤3 small functions —
  ~1 session, LOW risk (M5 §10 calls it "the only real work").
* Angle → radians: `theta = (coarse<<4 | fine) · 2π / 4096`.
* Build the 3×3, convert to quaternion for glTF (the kit's `fbx_skin.quat_to_euler_xyz` inverse machinery
  and `_quat_to_matrix` are right there to reuse/verify against).

**The validation is free and airtight (the project's own discipline):** the s52/s53 probe already logs the
creature's **composed bone-0 world matrix** each frame (`SfxMeshProbe.LogModels`, read at
`SFXDataMesh.cs:659`; the matrix is `*(MATRIX*)(SummonData+0x38)` bone 0 — M5 §9). Decode clip[k] at frame f
offline, compose the hierarchy with `R_anchor`/`T_anchor` taken from that frame's logged anchor
(`SummonData+0x40`, already logged), and compare bone 0 against the probe row. If they match, the Euler order
is **confirmed with zero playtests**; if not, the mismatch axis names the wrong RotMatrix. (Do NOT dump
`bones[1..92]` across a cast to "verify all bones" — that reconstructs the full stock skeletal animation and is
**BLOCKED**; bone 0 + the offline clip decode is sufficient and is the sanctioned read — M5 §9, D2 R6.)

### 2.5 What's missing between "decoded bytes" and "Blender-openable file"

Ranked; none blocks a first openable rig:

| # | gap | needed for | effort | note |
|---|---|---|---|---|
| 1 | **the angle→matrix Euler order** (§2.4) | correct animation | LOW | the one real decode; free to validate |
| 2 | **quad triangulation + winding** (FT4 → 2 tris; the negate-Y det=−1 reverses winding) | correct faces | trivial | `gltf.py:302-306` already reverses winding for the mirror |
| 3 | **UV normalization** | plausible UVs | LOW | pool `(u8 u, u8 v)` → glTF `[u/W, 1−v/H]`; the retarget REPLACES the mesh, so exact UVs are non-critical for the reference rig |
| 4 | **texture decode** (id-4 pages `64×128` 16bpp + CLUT strip → RGBA) | a good-looking preview | MED | M4 §7.5 gates it; ship a per-part neutral placeholder first (the pool RGB is neutral grey `80 80 80` anyway — M4 §9), decode pages as a polish pass |
| 5 | **the load-time UV V-offset bake** (M4 §5.4) | pixel-exact UVs | LOW | on disk we see PRE-bake UVs; apply `+= partTable[part].v` per part to match live |
| 6 | **coordinate convention** (PSX world → glTF Y-up) | upright in Blender | LOW | PSX is Y-down like FF9 field models → reuse `gltf._cpos`/`_cquat` **negate-Y**; verify the dragon stands upright, iterate if not (non-blocking) |
| 7 | **scale** | Blender-friendly size | trivial | reuse `DEFAULT_SCALE = 0.01` (creature bbox is ~hundreds of units, M4 §9 — same order as field models) |

**A first openable `.glb` needs only #1, #2, #3, #6, #7** — all LOW/trivial — with a placeholder texture. That
is the R2+R3 rungs (D2) packaged behind an `.glb` writer the add-on already reads.

### 2.6 Provenance of the exporter

The **tool is committable code** (parser + adapter + glTF writer — reads a caller-supplied local blob, emits a
file to a local path, embeds no game bytes) — same class as `ef_container.py`, `battle/camera_codec.py`. The
**exported stock-creature `.glb` is Square-Enix content → local-only** under
`C:/gd/SCRATCH/summon-transplant/` (the dir already exists, empty), exactly the battle-import precedent. The
CLI must default its output there and refuse to write a stock-creature export into the repo or a distributed
mod folder. The user's **own retargeted model is theirs to keep**.

---

## 3. THE RETURN TRIP — how the retargeted model comes back

The user opens the `.glb` in Blender, **retargets their mesh onto the dragon's `bone000..bone092` armature**
(weights their mesh to those bones, keeps the armature + the baked clips), and exports a `.glb` (the add-on's
**Export Model**, `model_ops.py:44`). Two endpoints:

### 3.1 The FileList FBX route (T1b, managed) — THE NATURAL ENDPOINT (PROVEN mechanism)

This is the rung-7 route already proven in-game ("our own rigged, animated FBX in a live battle"). The chain,
all in the kit's existing model pillar + the model-pillar C#:

1. **glTF → engine FBX + textures**: the kit's return path (`gltf.import_gltf` → `fbx_skin.emit_skinned_fbx` →
   `gltf._emit_model_to`, `gltf.py:694`) writes the engine-facing skinned FBX-ASCII the plugin loads via
   `ModelFactory.CreateModel(fbxPath, ...)` (`SFXDataMesh.cs:769`).
2. **baked clips → loose `.anim`**: the dragon's decoded motion, written as `.anim` JSON by the kit's
   **existing** `models/anim.clip_to_anim_json` (`anim.py:102`). Loaded at runtime as a Unity `AnimationClip`
   by `AssetManager.Load<AnimationClip>` and added to the FBX's `Animation` component
   (`SFXDataMesh.cs:781-783`).
3. **a `.sfxmodel` JSON** referencing the FBX + its `Animations` list (`ModelSequence.LoadFBX`,
   `SFXDataMesh.cs:976-1029`), fired by a battle `.seq` `LoadSFX`/`CreateVisualEffect` — the rung-1..7
   substrate.

**Why the retarget "just works":** Unity `AnimationClip`s bind curves **by bone hierarchy PATH**
(`SetCurve(bonePath, ...)`; `anim.py:10-19`, the `.anim` `"bone"` field IS the path). The dragon's baked clip
keys `bone000/bone001/...`. A user mesh weighted to a `bone000..bone092` armature with the **same hierarchy**
therefore binds every curve with **zero remap** — which is precisely "retarget your model onto the dragon's
rig." This is the same by-name binding the whole model pillar relies on (`extract.py:18-21`).

**What this delivers:** our retargeted mesh **deforming exactly like the dragon** (the skeletal layer). LOW
effort — it reuses proven kit code; the only new packaging is pointing the `model-import` deploy at the
SpecialEffects model slot + emitting a `.sfxmodel` that lists the clips, instead of writing to
`Models/{type}/{id}/`.

### 3.2 Native injection (T2 / W5) — the stock-grade endpoint, DEFERRED

Emit the retargeted mesh back into `ef###.bytes` as an id-4 + id-5 **model-package swap**, so the donor's MIPS
program drives OUR creature natively (D2 W5). This is the only path to PS1-native render parity, but it is
**HIGH effort**: it needs a geometry emitter (D2 G2), R5 (read the donor program to conform the rig — you
can't conform to a program you can't read), the container writer (W1), and the W0 load-gate; and it carries
W5's silent-failure conformance constraints (parent<child, single-scalar bone length, mesh ordinals,
≤6 parts, ≤7000 verts/mesh, model image ≤`0x50000`, **a rig violation hangs, not throws** — D2 W5). **Defer**
per the round's own recommendation.

### 3.3 The decision

**The FileList FBX route (§3.1) is the natural Blender-round-trip endpoint.** It is proven, DLL-free,
provenance-clean, and reuses the kit's `model-import` machinery almost verbatim. Native injection is the
someday-stock-grade path; it waits on R5 + W0 + a geometry emitter and is out of scope for "export them into
Blender."

### 3.4 Completing the faithful transplant (the layer decomposition — READ THIS)

The baked clip is the **skeletal** layer. To read as "the summon," two more layers compose on top, and neither
comes from the Blender file:

* **Staging** (the fly-down / fly-by / perspective-scale — M5 §8): the per-frame anchor `(rot,pos,scale)` the
  `.seq`/MIPS program feeds `Hi_DrawSummonModel`. Recoverable offline as the `.sfxmodel`'s **Movement /
  Rotation / Scaling** curves (`SFXDataMesh.cs:996-1000`; the JSON route already force-sets
  `transform.position` every frame at `:831`), authored from the s52 probe's **already-logged anchor rows**
  (`SummonData+0x40`, decomposed as `R·S` per M5 §8 Finding B — **use the column-norm scale**, the defect
  `root_reproject.py:43/75` silently drops). Do this and our FBX flies the dragon's path too, standalone.
* **Camera** (the native PSXCAM, 15 hard cuts, 47°→24° push-in — FORMAT.md §1.2/§2.5): inherited via the
  **Thomas-swap donor hybrid** — run the native donor with its forced `FixedCameraEffects` camera and
  `HideMeshes` the donor body, and our FBX renders *inside* that camera. (This is the existing hybrid; the
  Blender round-trip changes only WHAT renders, not the camera path.)

So the complete managed-lane faithful transplant = **retargeted FBX** (T3) + **baked skeletal clip** (T3) +
**anchor-trajectory `.sfxmodel` curves** (offline from the probe) + **donor hybrid for the camera**. T3 owns
the first two.

### 3.5 Relationship to the round's "leading candidate" (drive our mesh with the dragon's live bone matrices)

The orchestrator's leading candidate — pose our mesh each frame with the dragon's real per-frame bone matrices
read live from `*(SummonData+0x38)` — and this Blender round-trip are **two ways to the same place** ("our mesh
+ the dragon's animation"):

| | live-matrix (T1/T2 runtime) | Blender round-trip (T3, this slice) |
|---|---|---|
| when the motion is applied | per frame, at runtime, from the probe read | baked offline into a Unity clip |
| provenance | reads runtime skeleton state (sanctioned but per-frame) | authors a clip offline from the decoded motion (cleaner) |
| requires our rig to match the dragon skeleton | **yes** (to pose by its bones) | **yes** (to bind the clip by bone name) |
| the user's explicit ask | no | **yes** ("export them into Blender") |
| editability | none (live only) | full — scrub/edit the clip in Blender |

They are complementary, not competing: the live-matrix path is the runtime engine of the transplant; the
Blender round-trip is its **authoring surface** (and its provenance-cleaner sibling — the clip is authored
offline, never dumping per-bone runtime state). Both need the SAME thing T3 establishes: **a compatible
skeleton and a decoded clip.**

---

## 4. THE SKETCHED PIPELINE (concrete, committable)

```
# FORWARD — decode → Blender (committable tool; output LOCAL only)
summon-export ef227  --out C:/gd/SCRATCH/summon-transplant/bahamut.glb
    1. blob = read(local ef227.bytes)
    2. g   = ef_container.creature_geom(blob, mp)           # DONE — 93 bones / 2 meshes
    3. clips = summons.motion.decode_all(blob, mp, g)       # NEW — §2.4, self-validated vs probe bone-0
    4. model = summons.build.summon_model_struct(blob)      # NEW adapter — §2.2/§2.3
    5. summons.export.export_summon_gltf(model, clips, out) # reuses gltf.py emission + _gltf_io

# (user) Blender: Import Model bahamut.glb -> retarget THEIR mesh onto bone000..092 -> Export Model

# RETURN — Blender → game (managed FileList route; §3.1; reuses model-import)
summon-import my_creature.glb  --onto ef227  --deploy <mod>
    1. model  = gltf.import_gltf(glb)                       # DONE (kit)
    2. fbx    = fbx_skin.emit_skinned_fbx(model)            # DONE (kit)
    3. anims  = [ anim.clip_to_anim_json(c) for c in dragon_clips ]   # DONE (kit)
    4. write FBX + .anim + a .sfxmodel referencing them into the SpecialEffects model slot  # NEW packaging
    5. (optional) author .sfxmodel Movement/Rotation/Scaling from the probe anchor  # §3.4 staging
    #  camera + staging via the existing donor hybrid + HideMeshes
```

The NEW code is three small modules (`summons/motion.py`, `summons/build.py`, `summons/export.py`) + a
`.sfxmodel` emitter. Everything else is `ef_container.py` + the model pillar, both proven.

---

## 5. FALSIFIABLE PREDICTIONS / CHECKS (each can fail)

1. **Geometry sufficiency — PROVEN.** `ef_container.creature_geom(ef227)` already yields 93 bones / 2 meshes /
   1439 verts / 2416 faces / per-vertex bone via run-length. Re-run to confirm (done this slice).
2. **Rigid-skin → kit weights — PROVEN.** `bone_of_vertex(mesh)` gives one bone per vertex; `[[(b,1.0)]]` is a
   valid kit weight list; `emit_skinned_fbx` and `export_gltf` both consume it. Falsified if any mesh has
   `maxVertexIndex != nVert-1` (M4 §9 says never, 1041/1041).
3. **Bind-pose reconstruction — PROVEN math.** `W[b]·pool_vertex` with node rest `= (restRot[b],(0,0,length))`
   reproduces the renderer's `W[b]·pool_vertex`. Falsified only if the hierarchy recurrence in §2.3 differs
   from M5 §4 (it is cited to the instruction).
4. **Euler order — PLAUSIBLE, self-validating.** Decode clip[k]@frame f offline, compose bone 0 with the
   logged anchor, compare to the probe's logged bone-0 matrix. **Predicted:** they match within fp12 rounding.
   If not, the mismatched axis names the wrong `RotMatrix` (0x37a0/0x3850/0x3910). Zero playtests.
5. **Clip binds to a retargeted mesh — PLAUSIBLE (mechanism PROVEN).** A `.anim` keyed `bone000/...` binds by
   path to a user mesh weighted to a `bone000..092` armature (rung-7 by-name binding). Falsified if the user's
   armature renames/reparents bones — which is exactly the workflow instruction NOT to do (`model_ops.py:38`).
6. **Staging is a separate layer — PROVEN by M5 §5/§8.** The clip root translation spans ≤246 units; the
   40k-unit fly-by is the anchor, not the clip. **Predicted:** a baked-clip-only playback flaps/bends like the
   dragon but does not fly across the screen. Do not sell it as the whole cinematic (§0, §3.4).

---

## 5b. ADVERSARIAL VERIFICATION of §2.3 (claim T3-3) — CONFIRMED, fresh disasm

Independently re-derived the hierarchy recurrence from the user's own DLL (refkit fresh disasm of the
node builder's child loop `0x80aa..0x83c7`, x64) + read the kit's IBM/bindpose code. **The recurrence
matches M5 §4 byte-for-byte; the construction is exact. Refutation condition NOT met.**

* **`0x81aa` parent** — `movzx edi, byte ptr [rbp+3]` where `rbp = geom+0x18` (BoneLink rows), i.e.
  `BoneLink[k-1].parentBone`; then `shl rdi,5; add rdi,r13` = `&nodeBuf[parent]` = `W[parent]`. ✓
* **`0x8282` length** — the read at `0x827e` is `movsx eax, word ptr [rbp]` = `BoneLink.len` (s16 @ row+0);
  the store `0x8282 mov [rip+0x209dc8], eax` resolves to **rva `0x212050`** = the **Z** slot of the local
  translation SVECTOR (X/Y `0x212048/4c` were zeroed in branch-M setup `0x7abf`). So local translation is
  exactly `(0,0,length)`. ✓
* **`0x41e0` column mult** — called **three times** (`0x820a`, `0x8279`, `0x82d8`) reading `W[parent].R`
  (loaded from `rdi` at `0x81c0-0x81e7`) × the child's local `R` (from `nodeBuf[child]` at
  `0x81ed/0x81f6/0x8200`, the clip-written rotation) → `W[k].R = W[parent].R · localR[k]`. ✓
* **`0x3d60` RotTrans** — called at `0x836a` on the `(0,0,length)` vector → `W[k].t = W[parent].R·(0,0,length)
  + W[parent].t` (M5 §5: `0x3d60` verifiably adds the parent T register). ✓
* **Loop = index order** — `rsi` walks `r13+0x20 .. nodeBuf+N*0x20` step `0x20`; `rbp` steps `+4`
  (`0x8326`) → parent must precede child (no sort pass). ✓ (M4: 92/92 Bahamut rows satisfy parent<child.)
* **Vertex draw = `W[b]·v`** — fn `0x4eb0` composes `camR·boneMatrix[b]` via MulMatrix `0x3b60` @`0x51fa`
  (confirmed), then RotTransPers per vertex ⇒ bind-pose-in-model-space `= W[b]·pool_vertex`. ✓
* **Kit auto-IBM** — `gltf.py:190-206`: `world(name)` recomputes rest world = `parent_world · TRS(pos,quat,1)`
  (the SAME hierarchy operator), `inverseBindMatrices = _mat_inv(world(bone))`. `fbx_skin.py:14`: importer
  recomputes bindposes from `Lcl` TRS, self-checked per bone. ✓

**Algebra:** glTF/FBX with node local TRS `= (T=(0,0,length), R=restRot, S=1)` composes
`W[k]·p = W[parent].R·R[k]·p + W[parent].R·(0,0,length) + W[parent].t` — **identical** to the DLL. Then
`W_anim·inv(W_rest)·(W_rest·v) = W_anim·v` reproduces the renderer's `W_anim[b]·pool_vertex` exactly.

**Honest scope (does NOT refute):** the *construction* is exact and proven. The clause "reproduces
W_anim for the RIGHT dragon motion" inherits the §2.4 angle→matrix Euler-order dependency (PLAUSIBLE,
self-validating vs the probe bone-0) — the clip rotation feeding `W_anim` must be decoded correctly. That
is a separate open item; it does not affect the bind-pose construction, whose identity is coordinate- and
clip-independent. Verdict: **CONFIRMED / proven.**

## 6. PROVENANCE LEDGER (this slice)

* **No stock content committed.** This document quotes only structure — offsets, counts, bone/mesh/vert/face
  numbers, RVAs, struct layouts. No geometry, animation payload, texture, or container bytes were copied
  anywhere, and nothing was written into the repo. The one command run (`ef_container.py ef227.bytes`) read
  the local scratch blob and printed counts.
* **No DLL modified or redistributed.** Native claims are read-only static analysis of the user's own
  installed `FF9SpecialEffectPlugin.dll`, cited `fn@rva`; managed claims cite `file:line`.
* **The exporter is committable CODE; its stock-creature output is LOCAL-ONLY** under
  `C:/gd/SCRATCH/summon-transplant/` — the battle-import precedent. The CLI must default there and refuse to
  write a stock export into the repo or a distributed mod folder.
* **Reading the creature's per-frame bone-0 matrix to VALIDATE the offline decode is sanctioned** (choreography
  class, the s52 lane). **Dumping `bones[1..N-1]` across a cast is BLOCKED** — that reconstructs the stock
  skeletal animation as a redistributable asset. The offline motion decode (from the local container) is the
  motion source; the probe is only a validator.
* **The user's own retargeted model + the clips they build into their own mod folder at deploy time** are the
  verbatim-fork precedent — never committed, never redistributed. **Never produce or ship a patched
  `FF9SpecialEffectPlugin.dll`.**

---

## 7. REPRODUCTION

```
cd studies/custom-summons/thomas-swap/disasm
py ef_container.py C:/gd/SCRATCH/summon-format/ef227.bytes   # §1: 93 bones / 2 meshes / 1439 verts / 8 clips
# motion layout tiling (0 gaps / 0 overlaps), the clip spans a decoder walks:
py m5_chain.py C:/gd/SCRATCH/summon-format/ef227.bytes 0x7579c 0x7680c 0x77ae8 0x79064 0x7c3d8 0x7e3e8 0x825f8 0x87a84
```

Kit machinery the exporter reuses (read, do not re-derive): `ff9mapkit/models/gltf.py` (emission +
coord helpers), `models/_gltf_io.py` (`GltfBuffer`/`write_glb`), `models/fbx_skin.py` (`emit_skinned_fbx`),
`models/anim.py` (`clip_to_anim_json`), `blender/ff9mapkit_blender/model_ops.py` (Import/Export Model).

---

## 8. ADVERSARIAL VERIFICATION OF CLAIM T3-7 (independent re-derivation, 2026-07-23) — **CONFIRMED**

**Claim.** The baked motion clip is ONLY the skeletal layer; the large fly-by staging (73k-unit Z sweep,
0.02×–3.0× perspective scale) is the runtime anchor `(rot,pos,scale)` the `.seq`/MIPS program feeds Draw and
is NOT in the clip; the camera is a separate native layer (donor hybrid).
**Refute condition (stated):** a stock clip's root-translation track exceeding ~1000 units.

Re-derived from scratch against the local blob + a **FRESH** probe capture (this session's
`sfxmeshprobe.log`, 22 MB, dated 2026-07-23 — NOT the stale log M5 §8 cited). All three layers reproduce.

### Layer 1 — the clip carries only rotation + a tiny root drift (PROVEN)
`m5_roottrans.py ef227.bytes <8 clip offsets>` — the root-translation span of EVERY axis of ALL 8 Bahamut
clips: **max span 246 units (clip 8 Y, −285..−39), max abs value 285.** Every other track ≤237. This is
the falsification test, and it is **not met** (246 ≪ 1000). Not overfit: `m5_chain.py` confirms all 8 clips
**partition their span with 0 gaps / 0 overlaps** (2-byte "gaps" = alignment pad) — a wrong layout cannot
tile, so the decode that yields ≤246 is the genuine one.

### Layer 2 — the big staging is the anchor `DATA+0x40 = R·S`, a Draw argument (PROVEN)
`m5_scale.py` on the fresh ROOT rows (column norms of the logged `SummonData+0x40` matrix, `/4096`):
- **Scale is NOT unit** — column norms sweep **0.02 → 3.00** (a pure rotation would hold 1.0). So `+0x40`
  is `R·S`, exactly M5 §8 Finding B.
- **The fly-by**: frames 153–177, scale **3.0**, translation **Z = +23808 → −49152** = a **72,960-unit
  (≈73 k) Z sweep in 25 frames** — dwarfing the clip's 246-unit root track by ~300×.
- Mechanism: `Hi_DrawSummonModel(SVECTOR* rot, VECTOR* pos, VECTOR* scale, idx, loop)` (M5 §6) takes
  rot/pos/scale as **caller (`.seq`/MIPS) arguments**; `pose_eval@0x186a0` composes them into `+0x40`
  (scale applied `@0x187ab`). The staging is therefore a per-frame Draw input, not clip data.

### Layer 3 — the camera is a separate, independently-animating native layer (PROVEN)
`PSXCAM` rows: the projection distance `H` (∝ narrower FOV) takes **5 distinct values, 256 → 512** across
the cast (256 @ f90/130 → 415 @ f160–300 → 512 @ f450) — the ~47°→24° push-in, varying independently of
both the clip and the anchor. FORMAT.md §1.2 decodes it as its own sub-file (camera_codec round-trips).
The "donor hybrid" phrasing is the *delivery* mechanism (a sound integration choice, not a format fact);
the load-bearing, proven fact is that the camera is a separate native layer, absent from the motion clip.

### Verdict — **CONFIRMED** (was: proven). Both cited magnitudes are exact:
"73k-unit Z sweep" = measured 72,960; "0.02×–3.0× scale" = measured 0.02–3.00. Refute condition unmet
(clip root max 246). Scope note: measured on ef227 (Bahamut — the summon that motivated the round); the
layer split is structural (§4/§6/§10), not per-file, but only Bahamut was numerically re-measured.

---

## 8. ADVERSARIAL VERIFICATION — CLAIM T3-6 (the by-path binding return trip) — **CONFIRMED**

Independent re-derivation (not trusting the cited evidence; reproduced from the engine C# + kit source).
Verdict: **CONFIRMED** (was: proven). The binding MECHANISM is sound and independently reproduced; one
honesty caveat about "rung-7 proven" and the unbuilt dependencies is recorded below.

### 8.1 The managed render loop, traced end-to-end (the thing the mandate warned might be untraced)
* `SFXDataMesh.JSON.Begin` (SFXDataMesh.cs:769) `ModelFactory.CreateModel(tok.fbxPath, ...)` → for an FBX,
  `ModelImporter.CreateCustomModelFromFbx` → `CreateCustomModel`.
* `component.GetClip(animName)` (:778); if null, `AssetManager.Load<AnimationClip>(anim, false)` (:781) then
  `component.AddClip(clip, animName)` (:783) — the loose `.anim` is bound to the FBX's `Animation` component.
* `SFXDataMesh.JSON.Render`: `transform.position/eulerAngles/localScale` force-set from the `.sfxmodel`
  Movement/Rotation/Scaling (:831-833), then `Animation.Play(animName)` (:855) + `clipState.speed=0` +
  `clipState.time=…` (:856-857) + `Animation.Sample()` (:858) poses the skeleton for that frame.
  This is legacy Unity `Animation` (Play/Sample/AddClip/GetClip), which binds each curve by its **relative
  transform path** against the component's GameObject hierarchy — the mechanism the claim rests on.

### 8.2 The load-bearing link, reproduced from the DLL-side C# (not taken on the anim.py docstring's word)
`ModelImporter.CreateCustomModel` (ModelImporter.cs) builds exactly the hierarchy the `.anim` paths address:
* `:325` `baseObject = new GameObject(baseMesh.name)` — the Animation root.
* `:338` `bones[i] = new GameObject($"bone{anim.boneId[i]:D3}").transform` — bones named `bone000`,`bone001`,…
* `:343` root bones parent to `baseObject.transform`; `:349` child bones parent to `bones[parentIndex]` — a
  NESTED skeleton. So a bone's path from the Animation root is `bone000`, `bone000/bone001`, … — **exactly**
  the path `anim.py` emits (`bone_paths` anim.py:186-198; the `"bone"` field IS the `SetCurve` relativePath,
  anim.py:102-119, docstring :9-13) and exactly a source clip's Unity `m_RotationCurves[].path`. A user mesh
  retargeted onto that same `bone000..092` armature (kit-exported → same names + same nesting via the SAME
  `CreateCustomModel`) therefore resolves every curve with zero remap. **Binds for free — CONFIRMED.**

### 8.3 The refutation condition holds and is self-consistent
"WOULD BE REFUTED BY the retargeted armature renaming/reparenting bones away from bone000.." — this is exactly
what the workflow forbids: `model_ops.py:38-40` INFO string *"Keep the boneNNN bone names … don't rename/add
your own."* Rename or reparent → the path no longer resolves → the curve is silently dropped (legacy Unity).
The claim correctly scopes itself to the retarget-onto-the-existing-armature workflow.

### 8.4 Citations checked
* `SFXDataMesh.cs:769` CreateModel ✔ · `:781` `AssetManager.Load<AnimationClip>` ✔ · `:783` `AddClip` ✔
  (the cited `:781` is the Load; `:783` is the bind — both correct).
* `anim.py:10-19` correctly states the `"bone"` field is the FULL hierarchy PATH (not merely a leaf name) ✔.
* `model_ops.py:38` → the instruction is at :38-40 (close; correct file/intent) ✔.
* The corroborating fact: the kit's model-pillar anim edit loop relies on this SAME by-path binding and is
  in-game proven for character models — so the mechanism is not novel here, only re-applied to summons.

### 8.5 Honesty caveat (does NOT refute the claim, but the orchestrator must not over-read "proven")
* **"rung-7 proven"** = the FileList `.sfxmodel`→FBX→`ModelFactory` route renders an ANIMATED custom FBX in a
  live battle (a creature idling). It does NOT mean "the DRAGON's DECODED clip on a RETARGETED mesh in a summon
  cast" has literally been run. That specific composition depends on (a) the unbuilt summon-exporter (§2) and
  (b) the **PLAUSIBLE, not-yet-validated** angle→matrix Euler decode (§2.4). The *binding mechanism* is proven;
  the *composed summon pipeline* is not yet exercised. Claim T3-6 as stated is about the return-trip mechanism
  and its by-path rationale — that reasoning is fully sound — so CONFIRMED, but the full pipeline still owes the
  §2.4 decode + a first cast before anyone calls the whole transplant "in-game proven."
* The clip binds the **skeletal layer only** (§0/§3.4). Staging (fly-down/fly-by/perspective-scale) and the
  native camera are separate layers not carried by the `.anim`. Not part of this claim; flagged so the baked
  clip is never sold as the whole cinematic.

---

## 8. ADVERSARIAL VERIFICATION — CLAIM T3-8 (native injection = valid but HIGH-effort, deferred)

**Verdict: CONFIRMED** (one precision note). Re-derived independently from the user's own
`FF9SpecialEffectPlugin.dll` (x64) via `refkit` fresh disasm, from `M3-opcode-table.json`, and from Memoria C#
— NOT trusting the cited D2/FORMAT rows. Date 2026-07-23.

### What reproduced (PROVEN)
* **The hang is real and wired into the summon path.** `"HIRAISHI ERROR:"` string @`0x4b078`, `lea rdx` xref
  @`0x151c0` inside fn `[0x151a0,0x151ff)`. After formatting, control reaches a genuine infinite oscillating
  loop: `0x151f0 cmp rcx,rdx / 0x151f3 mov rax,r8 / 0x151f6 cmovne rax,rdx / 0x151fa mov rcx,rax /
  0x151fd jmp 0x151f0`. Both cited addresses are correct: FORMAT's `0x151a0` = the function entry, D2's
  `0x151f0` = the loop head. The stub is **called from 42 sites**, all in `0x15363..0x18b44` = the
  RegisterSummonModel (`0x15ee0`) / DrawSummonModel (`0x17740`) / bone-matrix (`0x18630`) subsystem. A NULL
  `data` pointer on the draw path therefore spins forever — **hang, not throw. PROVEN.**
* **≤7000 verts/mesh:** `0x50b3 cmp r13d,0x1b58` (0x1b58 = 7000) `jb <ok>` else error setup (`r8d,0x59`).
  PROVEN (strictly `< 7000`).
* **model image ≤ 0x50000:** `0x3e40d mov eax,0x50000 / sub eax,[rsi+0x10] / mov [rsi+0x48],eax` — keeps
  `0x50000 − modelBytes` as free space. PROVEN.
* **The donor program hard-codes rig slots (the R5-refutation axis fails).** `M3-opcode-table.json` confirms
  ops 26 `Hi_SetSummonMotion`, 100 `Hi_SetSummonMotFrame`, 149 `Hi_GetSummonBonePos`, 157
  `Hi_ShowSummonModelMesh`, 158 `Hi_HideSummonModelMesh`, 164 `Hi_GetSummonBoneMatrix`. These address meshes
  by bit-index and bones by number — so the program **inherently** references specific rig ordinals regardless
  of R5. The stated refutation ("R5 reveals the program does NOT hard-code rig constraints") is structurally
  unreachable: the constraint is guaranteed by the op-argument semantics.
* **Dependency chain matches.** FORMAT §4.3: W5 depends on `W1 + a geometry emitter + R5`; W1 depends on
  `R1 + W0`. So W5 transitively needs W0 — exactly the claim's "geometry emitter, R5, container writer W1, and
  the W0 load-gate." PROVEN self-consistent.
* **W0 is genuinely unrun.** Memoria `AssetManager.LoadBytesMultiple` routes `SpecialEffects/…` through
  `TryFindAssetInModOnDisc(..., GetResourcesAssetsPath(true)+"/")` (`AssetManager.cs:443/451/479/614`), and
  `SFXData.cs:170` loads from `SpecialEffects/ef{effNum:D3}/`. The override path is source-plausible but
  **never cast-tested** — the claim correctly lists W0 as an *unmet gate*, not as proven.

### Precision note (does not refute)
The claim's phrase "a rig conformance violation hangs rather than throws" slightly over-generalizes. Per FORMAT
§4.3, MOST conformance violations (parent≥child, wrong mesh ordinal, >6 parts) **render wrong SILENTLY**; only
the NULL-`data` case HANGS at HIRAISHI. The load-bearing point — **the DLL never throws a catchable exception;
the worst case is an unrecoverable silent hang requiring a debugger** — is correct and proven. Restate as
"violations either render wrong silently or hang; never a clean throw."

### Not refuted
Neither refutation condition is satisfied: W0 has not been shown to fail (it was never run, and the source trace
supports loadability), and R5 cannot reveal an absence of rig constraints because the op set encodes them.
The HIGH-effort / DEFER verdict stands on 4 unmet dependencies (G2, R5, W1, W0), each MED+, plus an offline-only
lint requirement forced by the silent-hang failure mode.
