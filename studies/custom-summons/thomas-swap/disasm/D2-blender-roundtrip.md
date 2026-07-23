# D2 — THE BLENDER ROUND-TRIP, MADE BUILDABLE (the concrete engineering plan)

**Slice D2.** T3 established that the Blender round-trip is *feasible* and *small*; this document turns it
into a **buildable spec**: the exact modules + function signatures to write, the verified struct contracts of
the kit code they plug into, the numbered user workflow, the return-path file layout, the ranked gap ledger
with effort/risk, the validation plan (mostly playtest-free), and the build order. It is the checklist a later
phase codes from.

**Relationship to the siblings — read this once.** There are two ways to "our mesh + the dragon's animation":
* **T1/D1 = the LIVE runtime lane** — a `memoria-patches` feature drives our mesh's bones each frame from the
  dragon's already-composed `*(SummonData+0x38)` world matrices. No offline clip. New engine code.
* **T3/D2 = the BLENDER AUTHORING lane** — decode the dragon's motion clip OFFLINE into a Unity `AnimationClip`,
  retarget in Blender, ship via the proven managed FileList/`.sfxmodel` route (rung 7). No new engine code.

They are **complementary, not competing** (T3 §3.5): the live lane is the runtime engine; the Blender lane is
the editable authoring surface *and* the provenance-cleaner sibling (the clip is authored from the local
container, never dumping per-bone runtime state). **D2 owns the Blender lane only.** Both need the SAME two
things D2 delivers: a **compatible skeleton** (bones named `bone000..bone092`) and a **decoded clip**.

All native RVAs are image-relative for the user's own `FF9SpecialEffectPlugin.dll` (x64, `ImageBase
0x180000000`). C# cites are relative to `C:/gd/FFIX/Memoria/Assembly-CSharp/`. Kit cites are relative to
`ff9mapkit/ff9mapkit/`. Confidence: **PROVEN** (verified this slice or a cited prior slice), **PLAUSIBLE**
(source-traced, one-step-inferred, unrun), **SPECULATIVE** (reasoned, unverified).

---

## 0. HEADLINE — what to build, in one breath

Three new committable modules + one new managed-return packaging step, riding entirely on `ef_container.py`
(the proven container/geometry parser) and the kit's proven model pillar (`models/gltf.py`, `_gltf_io.py`,
`fbx_skin.py`, `anim.py`) and Blender add-on (`blender/ff9mapkit_blender/model_ops.py`):

| # | thing to build | file | reuses | new LOC (est.) | risk |
|---|---|---|---|---|---|
| A | motion-clip decoder | `summons/motion.py` | — (the one genuine new decode) | ~150 | LOW, self-validating |
| B | container → kit Model-struct adapter | `summons/build.py` | `ef_container.py` + §2 math | ~120 | LOW |
| C | glTF emitter (pre-decoded clips) | `summons/export.py` + a `gltf.emit_model_gltf(...)` factor-out | `gltf.py` emission body, `_gltf_io` | ~60 + a refactor | LOW |
| D | return packaging (glTF → FBX + `.anim` + `.sfxmodel`) | `summons/deploy.py` | `import_gltf`, `emit_skinned_fbx`, `clip_to_anim_json` | ~120 | MED (new slot/`.sfxmodel` layout) |
| — | CLI verbs `summon-export` / `summon-import` | `__main__`/cli | the above | ~40 | trivial |

Everything the exporter needs from geometry is **already parsed and validated 372/372** by `ef_container.py`;
the only genuine new decode is the angle→matrix Euler composition (A), and its correctness is **free to check
offline** against the s52/s53 probe's already-logged bone-0 matrix (§4.1). The Blender import/export operators
are **unchanged** — the summon `.glb` is the exact same file `model-gltf` already produces, which the add-on's
Import Model already opens (`model_ops.py:34`, `bpy.ops.import_scene.gltf`).

---

## 1. THE VERIFIED PLUG CONTRACTS (why B/C/D are small — read before coding)

The whole plan hinges on the summon adapter producing the kit's **Model struct** exactly. I read both
consumers (`export_gltf` and `emit_skinned_fbx`) this slice; here is the contract they BOTH require, verified
field-by-field against `extract.read_model`'s output (`extract.py:419-486`, PROVEN):

```python
Model = {
  "geo":        str | None,      # stamped into mesh-node extras (export_gltf:296); None is fine for a summon
  "geo_id":     int | None,      # same; extras only, never routes for a summon
  "root_bone":  "bone000",       # must equal one bones[i]["name"]  (export_gltf:206, fbx_skin:149/204)
  "bones": [ {                   # ORDER = node order; parent must precede child (both consumers walk in order)
      "name":   "bone000",       # boneNNN — trailing digits ARE the FF9 bone number (anim binds by name)
      "parent": "bone000"|None,  # parent bone NAME (None = root)
      "pos":    (x, y, z),       # local translation, FF9 units  (summon: (0,0,length))
      "rot":    (x, y, z, w),    # local rest rotation quaternion (summon: identity OR clip[0]f0 — §2.3)
      "scale":  (1.0, 1.0, 1.0), # local scale
  }, ... ],
  "meshes": [ {
      "name":   "mesh0",
      "verts":  [(x, y, z), ...],          # BIND-POSE world verts (lifted — §2.2), FF9 units
      "normals": None,                     # PROVEN None-safe in both consumers (M4 §7.4: no usable normal)
      "uvs":    [(u, v), ...],             # 0..1 float, one per vert
      "submeshes": [ {"material_idx": int, "tris": [(a, b, c), ...]} ],   # a/b/c index THIS mesh's verts
      "weights": [ [(boneNum, 1.0)], ... ],# ONE per vert; rigid skin -> single (bone, 1.0). PROVEN valid.
      "parent": None,                      # nearest-ancestor mesh name; None = top-level (summons are flat)
  }, ... ],
  "materials": [ {"name": str, "texture": stem|None} ],   # texture = a PNG stem in textures{}
  "textures":  { stem: PIL.Image },        # placeholder grey is fine for a retarget reference (§6 gap #4)
}
```

**Why the rigid skin is a gift (PROVEN, M4 §4, corpus 1041/1041):** every summon vertex is hard-bound to
exactly one bone (`maxVertexIndex == nVert-1`), so `weights[i] = [(bone_of_vertex[i], 1.0)]` — no
normalization, no top-4 cap, no cluster ambiguity. `ef_container.bone_of_vertex(mesh)` returns the per-vertex
bone list directly (`ef_container.py:554-558`).

**Two contract gotchas found this slice (fold into `build.py`):**
1. **`submeshes` not `submesh`, each `{"material_idx", "tris"}`** — the T3 build.py sketch wrote `subs`; the
   real key is `"submeshes"` and each entry is a dict with `material_idx` + `tris` (`export_gltf:302`,
   `fbx_skin:249`, `extract.py:458-459`). `material_idx` indexes the flat `materials[]`.
2. **winding** — `export_gltf` reverses winding at emit (`gltf.py:307` `idx += [a, c, b2]`) because negate-Y is
   det=−1; `emit_skinned_fbx` negates the last poly index (`fbx_skin:246`). So `build.py` emits tris in the
   container's own order (CCW as stored) and lets each consumer apply its own flip — **do not pre-flip**.

---

## 2. THE ADAPTER MATH (module B, `summons/build.py`) — PROVEN

Straight from M4/M5, restated as the code to write. Every input is already in `ef_container.py`.

### 2.1 Bones (PROVEN — M5 §4)
```python
g = efc.creature_geom(blob, mp)            # 93 BoneLinks (ef_container.py:561)
# BoneLink: {length:s16, zero:u8, parent:u8}. Local translation is HARD-CODED (0,0,length); no rest rotation.
bones = []
for i in range(g.bone_count):
    if i == 0:
        parent, length = None, 0
    else:
        bl = g.bones[i-1]                  # bones[] holds boneCount-1 links, index i-1 for bone i (ef_container.py:463)
        parent, length = f"bone{bl.parent:03d}", bl.length
    bones.append({"name": f"bone{i:03d}", "parent": parent,
                  "pos": (0.0, 0.0, float(length)),
                  "rot": rest_rot[i],       # §2.3 (identity for MVP)
                  "scale": (1.0, 1.0, 1.0)})
```
**Constraint to assert (PROVEN, M5 §4):** `bl.parent < i` for every bone (parent precedes child — the hierarchy
pass walks in index order with no sort). A violated file is not stock; refuse it.

### 2.2 Mesh verts = BIND-POSE lift (PROVEN math — T3 §2.3, M4 §4)
The pool verts are **bone-LOCAL**. The kit's skin references verts in the bone's REST WORLD pose. So lift each
local vert by its bone's chosen rest world matrix `W[b]`:
```python
W = rest_world_matrices(bones)             # W[b] = W[parent].R·restRot[b], t chained via (0,0,length) — §2.3
for mesh m:
    bov   = efc.bone_of_vertex(m)          # per-vertex bone (run-length)
    local = list(efc.vertices(blob, g, m)) # (x,y,z,w) s16; drop w
    verts = [ affine(W[bov[i]], v[:3]) for i, v in enumerate(local) ]
```
This is exact because the renderer draws `W_anim[b]·pool` and posing the bound mesh reproduces it:
`W[b]·inv(W[b])·W_anim[b]·pool = W_anim[b]·pool` (glTF/FBX both recompute inverseBindMatrices from node rest —
`export_gltf:203`, `fbx_skin.py:14`). **PROVEN modulo §2.3's rest choice being internally consistent, which it
is for any choice** (the clip is absolute local rotation — §4.1).

### 2.3 The rest-pose choice (PLAUSIBLE, a design knob, not a gap)
`restRot[b]` — two self-consistent options (T3 §2.3):
* **IDENTITY (recommend for MVP):** rest = stick-figure; every clip fully poses the mesh. Simplest;
  `W[b].R = I`, `W[b].t = W[parent].t + (0,0,length)`. Verts land in a straight-hierarchy T-pose-ish layout.
* **clip[0] frame 0:** rest = a recognizable dragon in its first authored frame. Nicer for the user to skin
  against, but requires the motion decoder (module A) to *already* work, so it is a **phase-2 polish**, not the
  MVP. Ship IDENTITY first, add `--rest clip0` after A validates.

Either is correct because the animation channel is absolute; only the bind must match the chosen rest, and
`W[b]·pool` guarantees that by construction.

---

## 3. THE MOTION DECODER (module A, `summons/motion.py`) — the ONE genuine new decode

**Input:** `blob`, `mp` (ModelPackage), `g` (Geom). **Output:** the kit's clip shape (which `gltf.py`'s
animation loop and `anim.clip_to_anim_json` both already consume verbatim — `gltf.py:324-382`, `anim.py:102`):
```python
clip = { "name": "clip0", "sample_rate": 30.0, "length": <sec>,
         "bones": { boneNum(int): {"rot": [(t, (x,y,z,w)), ...],
                                    "pos": [(t, (x,y,z)), ...]   # bone 0 only
                                   } } }
```
> **Contract note:** `gltf.py`'s emitter keys `clip["bones"]` by **bone NUMBER (int)** and looks the node up via
> `joint_of_num` (`gltf.py:181`, `_select`/emit loop). `anim.clip_to_anim_json` keys by **hierarchy PATH string**
> (`anim.py:107`). For the FORWARD (glTF export) path use the **bone-number** shape; for the RETURN (`.anim`)
> path convert via `anim.bone_paths(model_bones)` (`anim.py:186`). `summons/export.py` handles the forward
> shape; `summons/deploy.py` handles the path shape. Keep motion.py emitting **bone-number** and convert at the
> `.anim` boundary — one direction of glue, already written in `anim.new_clip` (`anim.py:543`).

### 3.1 What is already PROVEN (M5 §2, byte-validated: clips tile with 0 gaps / 0 overlaps)
Per clip, per frame: three **12-bit Euler angles per bone** (`coarse<<4 | fine`, 4096 units/turn) + three
`s16` **root translation** tracks (bone 0 only). The bit-unpacking and the per-clip frame layout are decoded
and validated. `motion.py` reuses `m5_chain.py`'s span walker for the layout (repro in T3 §7).

### 3.2 The ONE unknown to read (PLAUSIBLE, bounded, ~1 session — M5 §2.3/§10)
The angle triple → local rotation matrix. Replicate the engine's three per-axis builders and their order:
* `RotMatrix` fns **`0x37a0` (a0)**, **`0x3850` (a1)**, **`0x3910` (a2)**, composed in that call order into an
  fp12 identity seed (M5 cites the call sites `0x7d8a/0x7d9a/0x7daa`). **Read from the DLL:** which axis (X/Y/Z)
  each builds, the sin/cos sign convention, and whether the product is `Ra0·Ra1·Ra2` or reversed.
* `theta = (coarse<<4 | fine) · 2π / 4096`; build the 3×3; convert to quaternion for the clip shape.
* Reuse the kit's `fbx_skin.setup_from_euler_xyz` / `quat_to_euler_xyz` (`fbx_skin.py:167-168`) to cross-check
  the quaternion once the axis order is known.

### 3.3 The validation is FREE and PLAYTEST-FREE (PROVEN discipline — T3 §2.4, M5 §9)
The s52/s53 probe already logs the creature's **composed bone-0 world matrix** each frame
(`SfxMeshProbe.LogModels`, read at `SFXDataMesh.cs:659`; the matrix is `*(MATRIX*)(SummonData+0x38)` bone 0).
Decode clip[k]@frame f offline, compose bone 0 with that frame's logged anchor (`SummonData+0x40`, also logged),
and compare to the probe row. Match within fp12 rounding ⇒ **the Euler order is confirmed with zero playtests**;
mismatch ⇒ the wrong axis names which `RotMatrix` fn is misordered.

> **PROVENANCE HARD LINE (PROVEN policy — M5 §9, T3 §6):** validate against **bone 0 ONLY**. Dumping
> `bones[1..92]` across a cast reconstructs the full stock skeletal animation as a redistributable asset and is
> **BLOCKED**. The offline clip decode (from the LOCAL container) is the motion source; the probe is only the
> bone-0 validator.

---

## 4. THE FORWARD PIPELINE (module C + CLI) — `summon-export`

### 4.1 The one refactor: factor `gltf.export_gltf`'s emission body out
`export_gltf` (`gltf.py:160`) is 90% reusable but coupled to `extract.read_model` (p0data4) and
`_select_anim_keys` (p0data5). Factor the emission body (skin/nodes/materials/mesh-primitives/animation-loop,
`gltf.py:198-420`) into:
```python
def emit_model_gltf(model: dict, clips: list[dict], out_path, *, scale=DEFAULT_SCALE,
                    bone_labels=True) -> dict:  # writes the .glb, returns a manifest
```
Then `export_gltf` becomes "read_model + _select_anim_keys → emit_model_gltf" and `export_summon_gltf` becomes
"build.summon_model_struct + motion.decode_all → emit_model_gltf". **The animation loop needs NO change** — it
already walks `clip["bones"]` and emits rotation/translation/scale channels keyed by bone number
(`gltf.py:324-382`), and a summon clip is that exact shape (§3). This refactor is behavior-preserving for real
models (regression-guard: byte-compare a `model-gltf zidane` before/after — the existing model tests cover it).

### 4.2 The CLI verb (committable code; output LOCAL-ONLY)
```
summon-export <ef### | path>  [--out DIR]  [--rest identity|clip0]  [--clips all|0,3]  [--no-tex]
   default --out = C:/gd/SCRATCH/summon-transplant/<name>.glb     # REFUSE a repo/mod-folder target (§7)
   1. blob  = read(local ef###.bytes)                              # user's own extract (ef_camera_decode.py / SCRATCH)
   2. c,mp,g = efc.parse_header / parse_model_package / creature_geom(blob)
   3. model = summons.build.summon_model_struct(blob, mp, g, rest=...)      # module B
   4. clips = summons.motion.decode_all(blob, mp, g)                        # module A
   5. summons.export.export_summon_gltf(model, clips, out)                  # module C -> emit_model_gltf
```
Output = the exact `.glb` the add-on's **Import Model** opens unchanged (`model_ops.py:34`).

---

## 5. THE USER WORKFLOW (the Blender round-trip, numbered) — the deliverable's UX

This is what ships in the pipeline doc; every kit/add-on op cited already exists except where marked NEW.

1. **Extract** your own `ef###.bytes` from your install (existing `ef_camera_decode.py`, or reuse a SCRATCH
   copy). *(Stock content — stays local.)*
2. **`summon-export ef227 --out .../bahamut.glb`** *(NEW verb)* → a local `.glb`: armature `bone000..bone092`
   + skinned mesh + the 8 baked clips.
3. **Blender → Import FF9 Model** (existing `model_ops.py:22`) → the dragon opens rigged + animated. Scrub the
   clips in the Dope Sheet to confirm the motion decoded (bind against `--rest clip0` for a recognizable pose).
4. **Retarget YOUR model onto the armature** — the one creative step. Weight your mesh to `bone000..bone092`,
   **keep the bone names and hierarchy** (rename/reparent = the clip won't bind — §6 gap #8, `model_ops.py:38`
   already warns "keep the boneNNN names"). Delete the dragon mesh; keep the armature + its Actions.
   * Best fit: a creature whose silhouette suits a 93-node long-necked flyer (another dragon / quadruped /
     serpent). A humanoid on a dragon rig is a **design** risk, flagged early (T1 §5 P4).
5. **Blender → Export FF9 Model** (existing `model_ops.py:44`, `export_yup/skins/animations/extras`) → a `.glb`
   + the printed `ff9mapkit summon-import ...` command *(the add-on's bridge needs one NEW arg branch — §6 #7)*.
6. **`summon-import my_creature.glb --onto ef227 --deploy <mod>`** *(NEW verb, module D)* → writes the FBX +
   the dragon's `.anim` clips + a `.sfxmodel` into the SpecialEffects model slot, fired by a battle `.seq`.
7. **In-game:** the donor-hybrid cast renders YOUR creature deforming like the dragon, inside the native camera.

---

## 6. THE RETURN PATH (module D, `summons/deploy.py`) — `summon-import`

The natural, proven endpoint is the **managed FileList FBX route (rung 7)** — DLL-free, provenance-clean, reuses
the model pillar almost verbatim (T3 §3.1). The chain, all-existing-kit except the packaging in bold:

1. **glTF → engine FBX + textures:** `gltf.import_gltf(glb)` (`gltf.py:523`, PROVEN round-trip — reads the skin,
   canonicalizes bone names to raw `boneNNN`, re-keys weights to bone number) → `fbx_skin.emit_skinned_fbx(model)`
   (`fbx_skin.py:144`) → FBX-ASCII the plugin loads via `ModelFactory.CreateModel(fbxPath, ...)`
   (`SFXDataMesh.cs:769`). *(This is exactly `_emit_model_to`, `gltf.py:694`, minus the `Models/{type}/{id}/`
   path — reuse it, override the dest.)*
2. **baked clips → loose `.anim`:** for each decoded dragon clip, `anim.clip_to_anim_json(clip_pathshape)`
   (`anim.py:102`) → `<slot>/....anim`. Convert motion.py's bone-NUMBER clip to the path shape via
   `anim.bone_paths(model["bones"])` (the model came back from `import_gltf`, so its skeleton is present).
3. **a `.sfxmodel` JSON** referencing the FBX + its `Animations` list (`ModelSequence.LoadFBX`,
   `SFXDataMesh.cs:976-1029`), and — for the flight/scale staging — its **Movement / Rotation / Scaling** curves
   (`SFXDataMesh.cs:996-1000`, force-set every frame at `:831-833`).
4. Fired by a battle `.seq` `LoadSFX`/`CreateVisualEffect` — the rung-1..7 substrate.

**Why the retarget "just works" (PROVEN mechanism — rung 7):** Unity `AnimationClip`s bind curves **by bone
hierarchy PATH** (`anim.py:9-13`, the `.anim` `"bone"` field IS the `SetCurve` relativePath). The dragon's baked
clip keys `bone000/bone001/...`; a user mesh weighted to a same-hierarchy `bone000..092` armature binds every
curve with **zero remap**. Same by-name binding the whole model pillar relies on (`extract.py` docstring,
`anim.py` module docstring).

**What D must build that the kit does NOT already have (the real new work):**
* **the SpecialEffects model slot layout** — where `ModelFactory.CreateModel` + `AssetManager.Load<AnimationClip>`
  probe for a summon-effect FBX/clip (the model pillar writes `Models/{type}/{id}/` + `Animations/{geoId}/`;
  the summon route may differ). **Read `ModelSequence.LoadFBX` (`SFXDataMesh.cs:976-1029`) + the FileList
  resolution to pin the exact path** — this is the MED-risk unknown, the one thing to verify before coding D.
* **the `.sfxmodel` emitter** — a small JSON writer (FBX ref + `Animations` list + optional Movement/Rotation/
  Scaling curves). Grammar is `ModelSequence.LoadFBX`'s reader; the rung-7 casts already produced hand-written
  `.sfxmodel`s to copy the shape from (`studies/custom-summons/` rung 7 artifacts).

### 6.1 THE STAGING LAYER — say it out loud so no playtest is wasted (PROVEN — M5 §5/§8, T3 §0/§3.4)
The baked clip is the **skeletal** layer ONLY: wing-flap, body-flex, the small ≤246-unit root drift. The big
**staging** — the fly-down, the ~73k-unit fly-by, the 0.02×→3.0× perspective scale — is the per-frame anchor
`(rot,pos,scale)` the `.seq`/MIPS program hands `Hi_DrawSummonModel` every frame, and is **NOT in the clip**. A
retargeted FBX playing the baked clip alone **flaps exactly like the dragon but does not fly across the screen.**
Two ways to supply staging, neither from the Blender file:
* **authored `.sfxmodel` Movement/Rotation/Scaling curves** — recoverable OFFLINE from the s52 probe's
  already-logged anchor rows (`SummonData+0x40`, decomposed `R·S` with the **column-norm scale** — the exact
  term `root_reproject.py:43/75` silently drops, M5 §8 Finding B). Do this and the standalone FBX flies the path.
* **the donor hybrid** (Thomas-swap) — run the native donor with its forced camera + `HideMeshes` its body; our
  FBX renders inside that camera + reads the native staging. Changes only WHAT renders, not the camera path.

So the complete managed-lane faithful transplant = **retargeted FBX** (D2) + **baked skeletal clip** (D2) +
**anchor-trajectory `.sfxmodel` curves** (offline from the probe) + **donor hybrid for the camera**. D2 owns the
first two; the staging curves are a follow-on (the ROOT probe already exists), the camera is the existing hybrid.

---

## 7. PROVENANCE — committable code vs local-only stock content (STRICT this round)

| artifact | class | where it lives |
|---|---|---|
| `summons/motion.py`, `build.py`, `export.py`, `deploy.py`, the CLI verbs, `.sfxmodel` emitter | **committable CODE** (parser/adapter/writer; reads a caller-supplied local blob, embeds no game bytes) — same class as `ef_container.py`, `battle/camera_codec.py` | the repo |
| a `gltf.emit_model_gltf` factor-out | **committable CODE** (refactor of existing kit code) | the repo |
| the exported stock-creature `.glb` (dragon mesh/rig/baked clips/texture) | **stock content → LOCAL-ONLY** | `C:/gd/SCRATCH/summon-transplant/` |
| the extracted `ef###.bytes` | **stock content → LOCAL-ONLY** | `C:/gd/SCRATCH/` |
| the USER's retargeted model + the clips they build into THEIR OWN mod folder at deploy time | **the user's, verbatim-fork precedent** — never committed, never redistributed | the user's mod folder |
| reading bone-0 matrix to VALIDATE the offline decode | **sanctioned** (choreography class, s52 lane) | — |
| dumping `bones[1..92]` across a cast | **BLOCKED** (reconstructs the stock skeletal animation as an asset) | — |
| a patched/redistributed `FF9SpecialEffectPlugin.dll` | **NEVER** (engine work stays on `memoria-patches/`; this lane needs NO DLL edit) | — |

**Hard CLI rule (matches T3 §2.6):** `summon-export` **defaults its output to `C:/gd/SCRATCH/summon-transplant/`
and REFUSES to write a stock-creature `.glb` into the repo or a distributed mod folder.** `summon-import` writes
the user's OWN retargeted model into the user's OWN mod folder — that is theirs.

---

## 8. VALIDATION PLAN (ranked; almost all playtest-free)

| # | check | how | when it fails |
|---|---|---|---|
| 1 | geometry sufficiency (PROVEN) | `efc.creature_geom(ef227)` → 93 bones / 2 meshes / 1439 verts / 8 clips (T3 §1 re-ran it) | never (validated 372/372) |
| 2 | rigid-skin → kit weights (PROVEN) | `bone_of_vertex` → `[[(b,1.0)]]`; feed `emit_skinned_fbx` | a mesh with `maxVertexIndex != nVert-1` (M4 says never) |
| 3 | bind-pose lift (PROVEN math) | `W[b]·pool` reproduces the renderer's `W[b]·pool` | only if §2.3 recurrence ≠ M5 §4 (cited) |
| 4 | **Euler order (the real check)** | decode clip[k]@f, compose bone 0 with the logged anchor, compare to the probe's bone-0 matrix | the mismatch axis names the wrong `RotMatrix` — **zero playtests** |
| 5 | `.glb` opens in Blender | add-on Import Model → armature + mesh + scrubbable clips | a malformed accessor (regression vs a real `model-gltf`) |
| 6 | forward refactor is behavior-preserving | byte-compare `model-gltf zidane` before/after `emit_model_gltf` | any diff (existing model tests guard) |
| 7 | clip binds to a retargeted mesh (PROVEN mechanism) | rung-7 by-name binding; the `.anim` `"bone"` path == the armature path | the user renamed/reparented bones (the workflow says don't) |
| 8 | staging is a separate layer (PROVEN) | baked-clip-only playback flaps but does not fly (M5 §5/§8) | — (this is expected; §6.1 owns it) |
| 9 | the `.sfxmodel`/slot path is right | first in-game cast renders the FBX (the ONE playtest) | wrong slot/FileList path — pin it BEFORE coding D (§6) |

The only in-game playtest is #9 (does the packaged FBX render), and rung 7 already proved the FileList route
renders an FBX in a live effect — so #9 is de-risked to "did D write the right paths," which #4-#7 gate offline.

---

## 9. BUILD ORDER (the dependency chain)

1. **A — `summons/motion.py`** (the Euler read + decoder) → **validate offline vs the probe bone-0 matrix
   (§3.3).** Blocks everything animated; ~1 session; the only real decode.
2. **B — `summons/build.py`** (adapter, IDENTITY rest first). Independent of A; can land in parallel (a
   static-pose `.glb` is a useful early artifact).
3. **C — the `gltf.emit_model_gltf` factor-out + `summons/export.py` + `summon-export` verb.** Needs B (and A
   for clips; a `--no-anims`/`--clips none` mode ships on B alone). Regression-guard the refactor (check #6).
4. **User step** — retarget in Blender (no code).
5. **D — `summons/deploy.py` + `.sfxmodel` emitter + `summon-import` verb.** First **pin the SpecialEffects slot
   path** (§6, read `ModelSequence.LoadFBX`), then wire `import_gltf` → `emit_skinned_fbx` → `.anim` → `.sfxmodel`.
6. **Add-on bridge arg** for the `summon-import` command string (`model_ops.py` Export → `bridge`).
7. **(follow-on, not D2)** staging `.sfxmodel` curves from the ROOT probe (§6.1) + the donor-hybrid camera.

**Deferred, explicitly OUT of D2 (T3 §3.2):** native injection (emit the retargeted mesh back into `ef###.bytes`
as an id-4/id-5 package swap so the donor MIPS drives OUR creature). HIGH effort — needs a geometry emitter, the
container writer, the load-gate, and it carries silent-failure conformance constraints (parent<child,
single-scalar bone length, ≤6 parts, ≤7000 verts/mesh, model image ≤`0x50000`, **a rig violation hangs, not
throws**). The someday-stock-grade path; the managed route above is the "export them into Blender" deliverable.

---

## 10. FALSIFIABLE PREDICTIONS

* **P1 (PROVEN):** `summons/build.py` on `ef227` yields a valid kit Model struct that `emit_skinned_fbx` accepts
  without the euler self-check raising — because the rest rotations are identity (or clip0) and the skin is
  rigid. *Falsified if* the euler self-check (`fbx_skin.py:174`) rejects an identity-rest bone (it cannot —
  identity round-trips exactly).
* **P2 (PLAUSIBLE, self-validating):** the decoded clip[k]@f composed at bone 0 matches the probe's logged
  bone-0 matrix within fp12 rounding once the `RotMatrix` axis order is read. *Falsified* → the mismatch axis is
  the misordered builder; bounded next step, not a guess.
* **P3 (PROVEN mechanism):** a `.anim` keyed `bone000/...` binds by path to a user mesh weighted to a
  `bone000..092` armature (rung-7 by-name binding). *Falsified if* the user renames/reparents bones — the
  workflow (and `model_ops.py:38`) says don't.
* **P4 (PROVEN, expected):** baked-clip-only playback flaps/bends like the dragon but does **not** fly across the
  screen — the ~73k-unit fly-by is the anchor, not the clip (M5 §5/§8). **Do not sell the clip as the whole
  cinematic** (§6.1). This is the T3 trap restated; it is a spec fact, not a bug.
* **P5 (the ONE unknown to de-risk before coding D):** the SpecialEffects FBX/clip slot path that
  `ModelFactory.CreateModel` + `AssetManager.Load<AnimationClip>` probe for a summon-effect model. Rung 7 proved
  an FBX renders via FileList; D2 predicts the same route serves the summon lane. *Falsified if* the summon
  effect resolves models through a different (native-only) path — then D degrades toward native injection (§9,
  deferred).

---

## 11. REPRODUCTION

```
cd studies/custom-summons/thomas-swap/disasm
py ef_container.py C:/gd/SCRATCH/summon-format/ef227.bytes     # 93 bones / 2 meshes / 1439 verts / 8 clips
py m5_chain.py C:/gd/SCRATCH/summon-format/ef227.bytes 0x7579c 0x7680c 0x77ae8 0x79064 0x7c3d8 0x7e3e8 0x825f8 0x87a84
```
Kit machinery the pipeline reuses (read, do NOT re-derive): `models/gltf.py` (`export_gltf`/`import_gltf` +
`_cpos`/`_cquat`/`_cnrm`/`_mat_*` + the animation loop `:324-382`), `models/_gltf_io.py` (`GltfBuffer`,
`write_glb`, `read_glb`, `read_clip`, `decode_accessor`), `models/fbx_skin.py` (`emit_skinned_fbx`,
`setup_from_euler_xyz`/`quat_to_euler_xyz`), `models/anim.py` (`clip_to_anim_json`, `bone_paths`, `new_clip`),
`models/gltf.py:_emit_model_to` (FBX+PNG writer), `blender/ff9mapkit_blender/model_ops.py` (Import/Export Model,
unchanged). The one committed summon parser: `ef_container.py` (`parse_header`/`parse_model_package`/
`creature_geom`/`vertices`/`bone_of_vertex`/`iter_primitives`).

---

## 12. PROVENANCE LEDGER (this slice)

* **No stock content committed.** This document quotes only structure — offsets, counts, RVAs, struct layouts,
  bone/mesh/vert numbers. No geometry, animation payload, texture, or container bytes were copied anywhere;
  nothing was written into the repo. No `ef###.bytes` was opened this slice (the counts are cited from T3 §1's
  prior run). No probe log was read.
* **No DLL modified or redistributed.** Native claims are read-only static analysis of the user's own installed
  `FF9SpecialEffectPlugin.dll`, cited `fn@rva`; C# claims cite `file:line`. **The Blender lane needs NO DLL
  edit** — it is 100% committable kit code + the proven managed FileList route.
* **The exporter is committable CODE; its stock output is LOCAL-ONLY** under `C:/gd/SCRATCH/summon-transplant/`
  (the dir exists, empty, confirmed this slice) — the battle-import precedent. The user's own retargeted model
  is theirs. Reading bone-0 to VALIDATE is sanctioned; dumping `bones[1..92]` is BLOCKED.
