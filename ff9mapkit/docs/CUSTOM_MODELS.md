# Custom Models — Export / Import Feasibility & Design

> **Status:** exploration / design brief (branch `custom_models`). No code yet; no in-game proof yet.
> **Scope:** FIELD & character models first; overworld (world map) as a follow-on. **Provenance:**
> operate on the user's own install, output to their disk, ship zero Square-Enix bytes (gitignore
> `*.fbx` / `*.anim` / textures, exactly like the battle-BG and world-mesh pipelines).
>
> This doc is grounded in a direct read of the Memoria source at the version-matched clone
> (`C:\gd\FFIX\Memoria`, pinned build `6b8bb2d5`) plus an adversarial verification pass. Every
> load-bearing engine claim carries a `file:line`. The "unknown until playtested" items are called
> out explicitly — the human owns in-game judgment (CLAUDE.md §2).

---

## 0. TL;DR — the premise flipped

The project's prior belief was *"custom models need a DLL build."* **That is stale.** Reading the
current engine source shows Memoria already ships a **complete custom-model FBX pipeline** — and it's
compiled into the build we already run:

- **The import seam is live and universal.** `ModelFactory.CreateModel` — the single choke point every
  field / character / battle / world model loads through — probes the mod folder for a loose
  `Models/{type}/{geoId}/{geoId}.fbx` **before** the bundle, and on a hit builds a fully skinned rig
  via `ModelImporter.CreateCustomModelFromFbx`. No `isBattle` gate, no DLL.
  (`Global/Model/ModelFactory.cs:56-71`.)
- **The importer is not static-only.** It reads an FBX skeleton, per-vertex bone weights, and
  bindposes; rebuilds the bone hierarchy (naming bones `bone000`, `bone001`…); creates
  `SkinnedMeshRenderer`s; and adds an `Animation` component. (`ModelImporter.cs:48-140, 323-401`.)
  The "static mesh, no skeleton" limitation the kit knows is specific to **battle backgrounds**
  (`ff9mapkit/battle/fbx.py` deliberately types the node `"Mesh"`), not characters.
- **Animations are stock Unity legacy `AnimationClip`s**, bound to bones **by name**
  (`bone{id:D3}`), with no bone-count/order requirement — only names must match
  (`AnimationClipReader.cs:120`, `AnimationFactory.cs:54-101`). FF9's own `ANH_` clips can drive a
  custom mesh that preserves the bone naming.
- **Custom `.anim` files also loose-load with no DLL.** `AssetManager.LoadFromDisc<AnimationClip>`
  routes to `AnimationClipReader.ReadAnimationClipFromDisc` (JSON or binary), and the asset system's
  own doc-comment lists `AnimationClip` among the types "read as plain files."
  (`AssetManager.cs:24, 421-423`.)
- This whole subsystem landed in Memoria commit **`9732e30e` "FBX model importer (#991)"**, an
  **ancestor of the pinned `6b8bb2d5`** — already in the engine we ship. The project simply never
  wired it up.

**Consequence for the two directions the owner asked about:**

| Direction | Difficulty | DLL? |
|---|---|---|
| **Import** a custom/edited model onto an existing GEO id | Mostly solved by the engine | **None** |
| **Export** a real model out to an editable file (fork fidelity) | The real new work — but tractable | **None** (offline UnityPy) |
| Custom **animation** takes (`.anim`) | Engine path exists | **None** (verify in-game) |
| **Mint a brand-new GEO id** (avoid shadowing a real one) | Small targeted patch | **Small** |
| Fix rigged-character deformation *if* the round-trip is wrong | Contained to `ModelImporter` | **Small–medium** |
| A brand-new playable **party member** | Enums/save/portraits — a Memoria fork | **Large — out of scope** |

**Shortest path to a faithful export→re-import loop (fidelity first):** write an offline UnityPy
exporter that emits a real GEO as a skinned FBX-ASCII → drop it *unchanged* at
`Models/{type}/{geoId}/{geoId}.fbx` → `SetModel` it and have the human confirm it renders **and
animates** identically. That single playtest is the make-or-break gate; everything downstream (edit,
scratch-author) is contingent on it.

---

## 0b. Implementation status (branch `custom_models`, updated during Phase 0)

**★★ Phase 0/1 PROVEN IN-GAME + ZERO-DLL CONFIRMED (2026-07-02): the export→re-import round-trip is COMPLETE
and needs NO engine change.** Two FF9 field characters (Vivi id 8, Zidane id 98) extracted by the kit →
skinned FBX-ASCII → re-imported render, skin, orient, move, **and animate identically on the user's
FULLY-STOCK Memoria** (a temporary diagnostic engine build was used to find the last bug, then reverted;
the pillar works with zero engine edits). Generality: 17/19 of a diverse offline batch (monsters, NPCs,
props, subs, mains) export cleanly.

**★ Robust bind correction (2026-07-02, in-game PROVEN).** Garnet (185) renders her ponytail scrunchie
(`rubber_band`) correctly AND walks correctly with the custom FBX — user-confirmed in-game. The former "a few
models mis-orient" gap turned out to be mis-diagnosed. The engine recomputes bindpose from bone-rest TRS and
assigns **one** bindpose array to **every** mesh (`ModelImporter.cs:356,388`), so a per-mesh authoring
transform has to be baked into that mesh's **verts**. Measuring the whole catalog
(`extract.bind_diagnostics`) showed the bake `G = boneWorld·m_BindPose` is **constant within each mesh**
(per-bone spread ≤~1e-6 across 522 models) but **differs between a character's SkinnedMeshRenderers** — e.g.
Garnet's body/hair are identity while her 38-vertex **`rubber_band`** (ponytail tie) is a 180° X-flip. The
old *global* bake saw the mix, gave up (`None`), and baked nothing → the odd mesh shipped flipped. Fix:
compute + bake **G per mesh** (`_collect` separates the walk from correction; `read_model` runs
`_bind_correction` on each SMR's own bindposes). This is exact — an offline **engine-skinning simulation**
test reproduces the original skin through animation even for a bone *shared* between two meshes with
divergent G. Catalog sweep: 522 models, 0 errors, 0 gaps, 517 unchanged, 26 divergent-SMR models corrected.
`_bind_correction` also upgraded from all-or-nothing to a **dominant rotation-family vote**, so the handful
of models with per-bone *jitter* (fields EFM 201/347, sub MRC 109, battle-form MON_B3_*) bake their majority
flip (~2° residual) instead of shipping 180°-wrong; it's never worse than no bake by bone count, and returns
`None` only when no family holds a majority (one scattered mesh in battle-monster 350).

**★★ New-GEO-id MINTING (2026-07-02, in-game PROVEN) — DLL-FREE.** Minting *adds* a brand-new GEO model id (a
fresh `SetModel` target) instead of *overriding* a real one — the gateway to placing net-new / edited models
by id. Like "import needs a DLL," the "minting needs a DLL" belief was stale: the pinned engine already ships
the pieces. **Register** with the `3DModel <id> <GEO_NAME>` DictionaryPatch directive (`DataPatchers.cs:574`
→ `FF9BattleDB.GEO[id]=name` at load; sibling `3DModelAnimation` registers custom anims). **Render**:
`SetModel(id)` → `GEO.GetValue(id)` → name → `GetModelType` (group→type) → `Models/{type}/{id}/{id}.fbx`, probed
on disc first (the loose-FBX importer). **Animate**: anims resolve by the *animation name's* tokens, not the
model's id — so a mint reuses any real model's animset by playing its `ANH_` names (our exporter keeps the bone
numbers so clips bind). Real GEO ids top out at 5511, so the mint band is **≥6000** (2-byte `SetModel` id; never
reuse a real *name* — it would hijack the reverse lookup). Proven in-game: id 6000 = a re-export of BBA idling in
the test field, additive (real BBA id 10 untouched). Kit: `models/mint.py`; a declarative **`[[mint]]`** block
(`id` + `from = "<GEO>"` re-export OR `fbx = "<path>"` custom model; optional `name`/`anims_from`) → the build
emits the `3DModel` line, stages the FBX, and auto-borrows the source's animset so a bare `[[npc]]/[[prop]]
model = <mintId>` needs no manual `anims`; CLI **`ff9mapkit model-mint <src> --id N [--deploy|--out]`**.
`deploy_field.py` now syncs the staged `Models/` tree + the mint directives.

**★ Blender edit loop — FORWARD half (2026-07-03, offline-validated; in-Blender check pending).** Hades Workshop
exports mangle the mesh and AssetStudio drops the animations; **`ff9mapkit model-gltf <model> [--anims] [--scale]`**
writes a self-contained **`.glb`** (glTF 2.0) Blender opens natively — clean skeleton + skin + textures + the
model's idle/walk/run clips, so a modder can scrub the walk cycle and edit the model. DLL-free (offline UnityPy).
The load-bearing conversion is Unity(left-handed, Y-up) → glTF(right-handed, Y-up) = a single-axis **negate-X**
mirror: positions/normals `(-x,y,z)`, quaternion **`(x,-y,-z,w)`**, reverse triangle winding + `doubleSided`,
`v→1-v` UVs, uniform scale bake `S≈0.01`, quaternion sign-continuity. Export the already-bind-corrected verts
verbatim and set `inverseBindMatrices[j] = inverse(boneWorld_rest[j])` (recomputed from the converted nodes) —
independent of the per-mesh bake G (which lives in the verts), so glTF's one-IBM-per-joint reproduces the correct
pose *and* animation, mirroring the engine; the rest-pose identity `world·IBM = I` is verified to 9.4e-08.
Animations read straight from the legacy `.anim` clips in p0data5 (quaternion rotation curves + root translation,
30 fps, LINEAR-faithful; `models/_gltf_io.read_clip`).

**★★ Blender edit loop — COMPLETE + in-game PROVEN (2026-07-03).** A user reshaped Vivi in Blender → glTF →
`model-import` → the edited Vivi renders in-game, still animating on the original skeleton — the full loop
(`model-gltf` → Blender → `model-import`) proven end-to-end, DLL-free. Blender-round-trip robustness: Blender
drops `asset.extras` + seam-splits verts (Vivi 1810→1843), so `model-import` auto-detects the source by matching
the mesh NAME (`GEO_MAIN_F0_VIV.001`) and auto-falls back from the v1 mesh-splice to a hybrid re-rig (keep the
pristine skeleton + id/type + textures, take the edited geometry + weights from the glTF) — so
`model-import <edited.glb> --deploy <mod>` needs zero flags. Edited glTF back into the game: **`ff9mapkit model-import <edited.glb> --like <GEO> --deploy <MODFOLDER>`** parses the glTF
(`_gltf_io.read_glb` + `decode_accessor`, byteStride/normalized-aware) → a Model struct via the *inverse*
conversion (negate-Y is an involution, so the same axis flip, `/scale`, un-reverse winding, un-flip UV) →
`fbx_skin.emit_skinned_fbx` → a loose-FBX override. Two modes: **v1 `--like <GEO>`** (recommended) keeps the
source's rig + weights + textures and splices in only the edited geometry (guards vertex-count-per-mesh
unchanged — reshape/retexture; textures are a direct PNG swap); **v2 full re-rig** (no `--like`) rebuilds
bones+weights from the glTF, remapping joints → FF9 bone numbers by node name (a non-`boneNNN` joint fails loud).
The **round-trip identity** `read_model → export_gltf → import_gltf` reproduces the struct to bones 1e-14 / verts
1e-5 (float32) / weights 1e-8 with 0 influence-set mismatches on Vivi *and* Garnet — proving the negate-Y
forward+inverse are consistent. The full WarpedEdge loop now exists end-to-end (`model-gltf` → Blender →
`model-import`); only in-game proof of an actual edit remains.

**★★ Multi-mesh characters — per-part named export (2026-07-03).** Making a *main character* like Garnet
robust exposed two engine facts + one export flaw:
- **The loose-FBX importer FLATTENS all meshes to siblings** under the base object (`ModelImporter.cs:390-391`:
  `meshGo.transform.parent = baseObject.transform`, unconditional) — it reads NO FBX mesh-to-mesh parenting.
  So a re-imported model can't reproduce a nested prefab hierarchy (e.g. Garnet's `rubber_band` scrunchie is a
  *child* of `long_hair` in the original prefab).
- **Mesh GameObject NAMES are load-bearing.** `ModelFactory.CreateModel` (`ModelFactory.cs:148-170`) runs a
  NAME-keyed branch for the 12 models in `garnetShortHairTable`: `GetChildByName("long_hair"/"short_hair")
  .GetComponentsInChildren<Renderer>()` disables one hair mesh by `ScenarioCounter>=10300` (or the `GarnetHair`
  ini). Lose the names and it NREs → hair renders as flailing spikes.
- **The old forward export FUSED all of a model's meshes into ONE glTF mesh** — so in Blender the user saw a
  single object; a proportional-edit on the shoulder dragged Garnet's 38-vert scrunchie (fused right next to it)
  out of shape (looked like the scrunchie "vanished"). And the return path could only recover part names by a
  fragile closest-vertex-count guess.

Fix: **`export_gltf` now emits ONE named glTF mesh + node PER FF9 part** (`long_hair` / `rubber_band` / `mesh0` /
`short_hair`), each stamped with `ff9_geo`/`ff9_mesh` node-extras. In Blender they're **separate editable objects**
(edit one without disturbing a neighbour), and the return path (`import_gltf`) **carries each part's name** (node
extra → node/object name → mesh name, `.001` stripped), so the re-rig restores names **by NAME** (`_restore_mesh_names`),
falling back to vertex-count only for genuinely-nameless parts. A nameless part gets a synthetic `__part{i}`
placeholder that can't collide with FF9's real `mesh0`/`mesh1` names. Round-trip verified faithful (max vert err
2.4e-5) with **name preservation across a 79-model sweep (0 fail)**; clean Garnet re-import deployed to
`FF9CustomMap` id 185 (mesh-splice, all 4 names intact) — awaiting the human's in-game look.

**KNOWN LIMIT (engine, not fixable via loose-FBX): late-game short-hair floating scrunchie.** Because the
importer flattens meshes AND assigns one material per mesh, a re-imported Garnet can't nest `rubber_band` under
`long_hair` NOR merge it in (the scrunchie is texture `185_0`, the hair `185_1`). So at `ScenarioCounter>=10300`
(short hair) the engine hides `long_hair` but the sibling `rubber_band` stays visible = a floating scrunchie.
EARLY game is perfect (short_hair hidden, ponytail+scrunchie shown). Only affects an *override* of the 12
hair-swap models viewed in a late-game short-hair scene; would need a small DLL change to fix (declined —
custom models stay zero-DLL).

The first proof was on Vivi (id 8): extracted → skinned FBX-ASCII → re-imported on **stock
Memoria's own importer** renders, skins, orients, moves, **and animates identically**. It took 4 in-game
iterations, each a real bug fixed **on the data side** (no engine change required): (1) a missing FBX node
colon (parse error → null model), (2) a root bone with a null parent (`ModelImporter.cs:108` NRE → worked
around with an "Armature" null-node parent), (3) a global 180°-about-X flip baked into `m_BindPose` that
the importer drops (fixed by baking `diag(1,-1,-1)` into verts), and (4) — the T-pose — the **cluster→bone
FBX connection was reversed**: Memoria links it via `GetFirstConnectedIndex(clusterId, asChild=false)`,
which wants `C: "OO", boneId, clusterId` (reversed from the standard cluster-child-of-bone convention), so
my standard-direction connection linked zero subdeformers → `GetBoneWeights` returned null → `hasAnim=false`
→ `anim=null` → `CreateCustomModel` skipped the whole skeleton → the mesh rendered as raw un-skinned verts
(0 bones) = T-pose. **All four were emitter fixes; import needs no DLL.** The export half:

- **`ff9mapkit model-export <GEO|id> [--out DIR | --deploy MODFOLDER] [--flat]`** — reads a real model
  from `p0data4.bin` and writes a **skinned FBX-ASCII** + PNG textures in the engine override layout
  `Models/{type}/{geoId}/{geoId}.fbx`. New package `ff9mapkit/models/` (`extract.py` → in-memory model,
  `fbx_skin.py` → the emitter, `export.py` → orchestrator). Offline tests: `tests/test_model_export.py`.
- **Proven on `GEO_NPC_F1_BBA` (id 10):** 2 meshes / 518 verts / 23 bones / 2 textures; extraction
  re-rendered as coherent character geometry in Blender (verifies the vertex-stream decode); the
  **quaternion→euler(XYZ) conversion is self-checked exact (max err 6.6e-08)** against Memoria's
  `SetupFromEulerAngles`.

**Empirical findings from implementation (refine/correct §2–§5 below):**
1. **Field/char model prefabs live in `p0data4.bin`** at `assets/resources/models/{typeInt}/{geoId}/{geoId}.fbx`
   as native Unity `GameObject`s. Structure: a root GO (`Transform` + legacy `Animation`) → bone GOs
   (`bone000`..) + one mesh GO **per submesh group**, each a `SkinnedMeshRenderer` with its *own* bone
   subset. `m_Skin` per-vertex `boneIndex[]` indexes that SMR's `m_Bones`; each resolves to `boneNNN` —
   the exporter remaps weights to the **FF9 bone number** (skeleton-order-independent).
2. **Vertices use multiple 16-byte-aligned streams** (Unity 5.2.3): e.g. stream 0 = pos+normal+tangent,
   stream 1 = uv0, packed as consecutive per-stream blocks — a single-stride read is WRONG. Skin weights
   are a **separate `m_Skin` array**, not in the vertex stream. (`models/extract.py` handles streams + float16.)
3. **`FbxSkeleton` hard rule:** the `Root`-typed node is forced `BoneId=0` and `assignedBoneNameIds`
   starts `{0}`, so **no `LimbNode` may end in `000`**. FF9's armature root *is* `bone000` → type it
   `Root`, every other bone `LimbNode` named with its real number.
4. **Blender reads only BINARY FBX, not ASCII** (Blender 5.1: *"ASCII FBX files are not supported"*) —
   the recon's "Blender imports ASCII" claim was **wrong**. The engine's `ReadFlexible` reads **both**.
   So ASCII FBX is correct for the engine round-trip (fork fidelity, the priority) but **the Blender edit
   loop (Phase 3) needs binary FBX or glTF** — see the revised decision in §8.

## 1. The format truth  *(verdict Q1: CONFIRMED against source)*

FF9 PC field/character models are **native Unity assets**, not a custom SE binary. There is nothing
bespoke to reverse-engineer — UnityPy/AssetStudio read the mesh, skeleton, bindposes, skin weights,
and `AnimationClip`s directly.

- Single load choke point: `ModelFactory.CreateModel` (`ModelFactory.cs:50`). Name → path via
  `GetRenameModelPath` → `"Models/{(int)ModelType}/{geoId}/{geoId}"` (`:34`). `geoId` from the
  two-way dict `FF9BattleDB.GEO` (`FF9BattleDB.GEO.cs:6`); `ModelType` from the 2nd `_` token of the
  GEO name.
- The bundle branch is literally commented `// Model serialized in an Unity archive`, then
  `AssetManager.Load<GameObject>(...)` → `Object.Instantiate` (`:70-74`). The returned prefab is
  already skinned — `model.GetComponentsInChildren<SkinnedMeshRenderer>()` (`:123`) — and has a real
  named transform hierarchy (the garnet long_hair/short_hair block, `:148-169`).
- `geo.cs` is runtime helpers only (scale / attach / mesh-hide flags). **No PSX `.geo`/`.tim` parser
  exists on PC.**

**`ModelType` enum → folder number** (verified `Global/Model/ModelType.cs`):

| GEO group token | `ModelType` | Folder int | On-disk path |
|---|---|---|---|
| `GEO_ACC_*` | `acc` | 1 | `Models/1/{geoId}/{geoId}.fbx` |
| `GEO_MAIN_*` | `main` | 2 | `Models/2/{geoId}/{geoId}.fbx` |
| `GEO_MON_*` | `mon` | 3 | `Models/3/{geoId}/{geoId}.fbx` |
| `GEO_NPC_*` | `npc` | 4 | `Models/4/{geoId}/{geoId}.fbx` |
| `GEO_SUB_*` | `sub` | 5 | `Models/5/{geoId}/{geoId}.fbx` |
| `GEO_WEP_*` | `battle_weapon` | 6 | `BattleMap/BattleModel/6/{geoId}/{geoId}.fbx` |

(geoIds 429/430 are force-mapped to `sub`; `GEO_WEP*` route to the BattleModel tree — see
`ModelFactory.cs:26-34`.) Root under the mod folder is
`StreamingAssets/Assets/Resources/`, resolved by `AssetManager.SearchAssetOnDisc` across all
`FolderNames` (`AssetManager.cs:790-814`).

**Discount the stale wiki claim.** The Memoria wiki line *"3D models may not be replaced by external
files"* is contradicted by the current source — `CreateModel` demonstrably loads a loose `.fbx`
first. Trust the source, not the wiki.

---

## 2. Import path — reuse, don't rebuild  *(verdict Q2: CONFIRMED)*

The engine already imports a rigged FBX and prefers it over the bundle. **No DLL to override an
existing GEO id.**

```
ModelFactory.CreateModel(geoName)
  └─ externalPath = AssetManager.SearchAssetOnDisc("Models/{type}/{geoId}/{geoId}.fbx")   // mod folders, high→low
     ├─ hit  → ModelImporter.CreateCustomModelFromFbx(externalPath)     // YOUR model (skinned)
     └─ miss → AssetManager.Load<GameObject>(...)                        // stock bundle prefab
  └─ AnimationFactory.AddAnimToGameObject(model, geoName, …)             // binds ANH_ clips by name
```

- Proven callers exercise the **field/character** path (all `isBattle=false`):
  `EventEngine.updateModelsToBeAdded.cs:25` (field actor spawn, `gMode==1`),
  `EventEngine.DoEventCode.cs:1060` (the `SetModel` opcode `0x2F` handler),
  `FieldMap.cs:482` (loads Zidane `GEO_MAIN_F0_ZDN`).
- **File convention:** `…/Resources/Models/{typeInt}/{geoId}/{geoId}.fbx` + textures as PNG in the
  same directory (the material `%.png` disc-probe reskins from there, `ModelFactory.cs:100-116`).
- **Deploy mechanism already exists in the kit** — the battle-BG FBX and world-mesh pipelines already
  drop loose files into the mod folder and gitignore them; reuse that plumbing.

---

## 3. Export path — fork fidelity FIRST

The engine has an FBX **writer** (`FbxIO.WriteAscii/WriteBinary`, GPL hamish-milne lib) but **no
GameObject→FBX mesh export** — the in-engine ModelViewer only exports *animations* (`.anim`, the "E"
key). So mesh export is **the gap**, and it belongs offline in the kit.

**Tool:** a new offline UnityPy pass over the user's `p0data`, mirroring `ff9mapkit/battle/extract.py`
(which already decodes packed Unity `m_VertexData`/`m_SubMeshes` via `_decode_mesh`, and already knows
the *"do NOT use UnityPy's OBJ export — winding is wrong"* gotcha). Run on request, write to the
user's disk, gitignore outputs.

**Pipeline (per GEO id):**
1. Resolve `GEO_<grp>_<form>_<token>` → `geoId` + `ModelType` → bundle asset path
   `Models/{typeInt}/{geoId}/{geoId}` (the kit already has the id↔name map in `_modeldb.py`).
2. Read the prefab: for each `SkinnedMeshRenderer` → `sharedMesh` (verts, tris, normals, tangents,
   uv, colors, **boneWeights**, **bindposes**) + the `bones[]` Transform hierarchy (name, parent,
   local TRS).
3. Emit **FBX-ASCII** — a new **skinned emitter** (extend `battle/fbx.py`). Bones become
   `LimbNode`/`Root` Model nodes named so they re-import as `bone###`; each mesh gets a
   `Skin`+`Cluster` Deformer carrying vertex indices + weights + a `TransformLink` bind matrix.
4. Emit textures as PNG alongside.
5. Optionally emit the model's `ANH_*` clips as `.anim` in `AnimationClipReader`'s JSON schema
   (per-bone `localRotation`/`localPosition`/`localScale` curves + tangents; `ParseToJSON` proves the
   round-trip). Note: FF9 stores clips numerically under `Animations/{geoId}/{animKey}`, mapped by
   `FF9DBAll.AnimationDB` — the kit's `catalog.py` model→anim join already uses the same
   `ANH_<grp>_<form>_<token>` key.

**Lossy / watch-outs:**
- **≤4 bone influences per vertex** — `FbxSkeleton.RegisterWeight` drops the 5th. *Confirm no real
  GEO exceeds 4 weights/vertex before claiming byte-lossless.*
- **`Mesh.isReadable`** — an *in-engine* dumper couldn't read a non-readable uploaded mesh; the
  **offline UnityPy path sidesteps this** (it reads serialized bytes, not the GPU mesh). This is the
  decisive reason to export offline, not from a debug key.
- **Root-bone / non-uniform bone scale** — the importer has an explicit TODO here
  (`ModelImporter.cs:111`, *"the only way to properly support this is to create intermediate
  GameObjects"*). An export can *preserve* them, but re-import may not reproduce them. The fidelity
  verdict lands right here.

**Community precedent (from the web survey):** the community solved model **export** long ago —
*Reverse FF9* (tasior) and the *Chevluh FF9 Blender importer* read the PSX `ff9.IMG` and produce
fully rigged, animated models — but custom rigged model **import**, especially for *field* models, is
essentially **unsolved** at the geometry level. Hades Workshop's Unity Assets Viewer can dump the PC
prefabs to FBX-ASCII, but its *import* is byte-round-trip only and corrupts on edit. So: we can lean
on precedent (or the even-simpler native-Unity path on PC) for export, and we'd be **pioneering
rigged field-model import** — consistent with this kit having pioneered custom fields.

---

## 4. Animation strategy  *(verdict Q4: CONFIRMED)*

**Mechanism:** native Unity **legacy** `AnimationClip` on an `Animation` component. FF9 never lets
Unity advance time — it computes an integer `animFrame` itself, sets `animState.speed = 0;
animState.time = frame/max * length`, then `Animation.Sample()` for a single pose
(`btl_mot.cs:221-233`; field mirror `fldchar.cs:271-282`; `ProcessAnime` drives `animFrame`,
`EventEngine.ProcessAnime.cs`). A custom clip's `frameRate × length` therefore sets the frame count
the engine iterates (`GeoAnim.cs:23-38`).

**Binding is by bone NAME, loosely:**
- Curves target bones by name: `clip.SetCurve(boneName, typeof(Transform), "localRotation.x"…)`
  (`AnimationClipReader.cs:120, 224-239`). Unmatched curves are silently ignored → **bone
  count/order need not match; only names must.**
- The engine relies on this itself: `animationPathTable` (`AnimationFactory.cs:151-255`) shares one
  clip folder across many GEOs; `AddAnimToGameObject` attaches clips purely by string name with **no
  compatibility check** (`:68-101`).
- Bones are `bone{id:D3}`; other engine code looks them up the same way
  (`GetChildByName("bone"+i.ToString("D3"))`, `btl_mot.cs:248`, `geoAttach`). The FBX importer parses
  the **trailing 3 digits of the FBX bone name** as the bone id (`FbxSkeleton`), so exported bone
  names must be `bone###`.

**Invariants any export/import MUST hold (the fidelity linchpin):** bones named `bone000, bone001,…`
+ a consistent hierarchy + bindpose. You do **not** need to preserve FF9's exact bone count/order —
only the naming so stock/donor `ANH_` clips bind.

**Can we ship model+animation as one file?** Yes — either one skinned FBX (mesh + rig + takes), or
geometry as FBX + animation as sidecar `.anim`. The `.anim` reader handles JSON or the binary `.anim`
serialized format (as found in `p0data5.bin`).

**Custom `.anim` loose-load is DLL-free** — resolved contradiction: `AssetManager.LoadFromDisc<T>`
routes `AnimationClip` to `AnimationClipReader.ReadAnimationClipFromDisc` (`AssetManager.cs:421-423`),
and the header doc-comment (`:24`) explicitly lists `AnimationClip` as a plain-file type. (The recon
agent that said "ModelViewer-only" was wrong.) **Unknown until playtested:** whether a *loose FBX
field character* actually receives its `ANH_` clips in practice (proven only for static battle meshes;
the code path exists but is unexercised for skinned field chars).

---

## 5. DLL scope

**Core loop — export → faithful re-import → edit → reskin/new-geometry on an EXISTING GEO id: ZERO
DLL.** The load seam and skinned importer already exist and are universal.

A DLL is only needed for these, each small (s23–s33 targeted-patch scale) or a separate fork task:

| Want | DLL work | Size |
|---|---|---|
| Load a loose custom model on an existing GEO id | none | — |
| Load custom `.anim` takes | none (verify §4) | — |
| **Mint a new GEO id** (no shadowing a real model) | add id↔name to `FF9BattleDB.GEO` + a registration directive so `GetGEOID`/`GetModelType`/`GetRenameModelPath` resolve it | small |
| Fix rigged-character deformation if the round-trip is wrong | resolve `ModelImporter.cs:111` root-bone / non-uniform-scale TODO | small–medium, contained to `ModelImporter` |
| New playable **party member** | fixed `CharacterId`/`SerialNumber`/`PresetId` enums 0–11 + save layout + portraits + `SetupPartyUID`; dormant `CharacterBuilder.Spawn` exists but its only caller is hard-disabled | **large — a Memoria fork, OUT of scope** |

Follow the s23–s33 idiom: **wrap, don't rewrite.**

---

## 6. Field vs World

**Same backbone, not a separate pipeline.** Overworld actors are the same Unity
`SkinnedMeshRenderer` GameObjects minted by the same
`ModelFactory.CreateModel(FF9BattleDB.GEO.GetValue(model), …)`;
`updateModelsToBeAdded.cs` dispatches field (`gMode==1`), world (`gMode==3`), and battle through it
identically. World characters are the **W-form subset** (`GEO_SUB_W0_001` Zidane … `_010`) with
`ANH_SUB_W0_*` clips on the same legacy `Animation` component (`WMActor.cs`).

**Why field first:** it's the north-star fidelity axis, the `SetModel` authoring surface is already
rich (`_modeldb.py` / `archetypes.py` / InfoHub), and field has zero extra plumbing. **World deltas
(follow-on):**
- **Scale** — `WMActor.SetScale` uses 0–64 ints × `1/256` with per-actor overrides.
- **Position** — world 256× fixed-point + block-wrap, vs field `frame="world"` walkmesh coords.
- **`SmoothFrameUpdater_World`** — an optional 60fps Lerp layer (not a distinct anim driver);
  skippable via the `Skip` idiom already understood from the F6 overworld work.
- **Net-new world actor registration needs DLL** — `WMActor.Initialize()` / `WMAnimationBank`
  hardcode the ~6 world actors. **Reskinning/swapping an existing world actor's GEO needs no DLL.**

Build the field export/import codec once; it transfers to world geometry/skeleton/clips wholesale.
World then gets a thin scale/position adapter + (only for net-new actors) a registration patch.

---

## 7. Phased plan

Each milestone marks **DLL vs no-DLL** and what **"in-game proven"** means (the human playtests).

**Phase 0 — Export a real model to an editable file. `no-DLL`.**
Offline UnityPy exporter reads one field character GEO (start with an NPC) from the user's `p0data`,
writes a skinned FBX-ASCII (bones `bone###`, weights, bindposes) + PNGs.
*Proven when:* the FBX opens in Blender with a correct skeleton + skinned mesh + textures.
*(Agent-verifiable via a headless Blender import — no game needed yet.)*

**Phase 1 — FIDELITY: re-import the UNCHANGED model. `no-DLL` (unless the importer TODO bites).**
Drop the byte-unedited FBX at `Models/{type}/{geoId}/{geoId}.fbx`, `SetModel` that GEO.
*Proven when:* the human confirms it renders **and animates via its stock `ANH_` clips**
indistinguishably from the bundled model. **This is the make-or-break gate.**
- If deformation is wrong → small/medium DLL for `ModelImporter.cs:111`, then re-test.
- If stock clips don't bind → check `bone###` naming/hierarchy parity first (data fix, likely no DLL).

**Phase 2 — Custom ANIMATION round-trip. `no-DLL` (verify §4).**
Export a stock `ANH_` clip to `.anim` (JSON), re-import unedited at `Animations/…/<ANH…>.anim`.
*Proven when:* the human confirms the loose `.anim` plays identically. If not → small DLL to route
`AnimationClipReader` into the clip-load path.

**Phase 3 — EDIT. `no-DLL` (assuming Phase 1–2 green).**
Round-trip an *edited* mesh (move a vert / repaint) and an *edited* clip.
*Proven when:* the human sees the edit in-game, no other regression. Blender add-on gets
"Import FF9 Model / Export FF9 Model" operators (reuse the add-on's marker/IO scaffolding).

**Phase 4 — SCRATCH AUTHOR on an existing GEO id. `no-DLL`.**
Ship a wholly new mesh + rig reusing a donor GEO's `bone###` names (so stock clips drive it) or ship
new `.anim` takes. *Proven when:* the human walks a brand-new custom model in-game, animated.

**Phase 5 — MINT a new GEO id (`small DLL`) + WORLD follow-on (`no-DLL` to reskin).**
Add a `FF9BattleDB.GEO` entry + registration directive so a new model owns its id (no shadowing).
Port the codec to world (scale/position adapter). *Proven when:* the human `SetModel`s a minted id
in-field, and separately sees a reskinned overworld actor.

---

## 8. Open questions / decisions for the owner

1. **Fidelity gate acceptance (Phase 1):** does an unedited round-tripped rigged FBX deform + animate
   identically in-game? This one playtest decides whether the pillar stays DLL-free or needs the
   `ModelImporter.cs:111` fix. **Build nothing downstream before this returns.**
2. **Interchange format — DECIDED FBX-ASCII for the engine; the edit loop needs a second format.**
   FBX-ASCII is the engine-native export target (the importer's `ReadFlexible` reads it) and Phase 0
   ships it. **Correction to the recon:** Blender does NOT read ASCII FBX (only binary) — so the
   *edit* loop (Phase 3) needs one of: (a) a **binary FBX** emitter (the engine reads binary too, so one
   file would serve both — but a Python binary-FBX writer is the larger lift), or (b) **glTF** for
   Blender + a glTF→ASCII-FBX bridge on the way back in. Recommend deciding at Phase 3 once the Phase-1
   engine round-trip is confirmed; fork-fidelity (the priority) is unblocked by ASCII today.
3. **Mint-new-id vs shadow-existing:** is per-model DLL-minting of new GEO ids in scope, or is
   overriding / donor-reusing existing ids enough for the intended content? (Overriding is DLL-free
   and covers most NPC/prop/reskin cases.)
4. **Party-member boundary:** confirm a *new playable party member* stays **out** of this pillar
   (it's a Memoria fork — enums 0–11 + save layout + portraits). This pillar delivers custom
   models/props/NPCs/overworld reskins, not new party slots.

---

## 9. What to reuse

- **`ff9mapkit/battle/fbx.py`** — the ASCII-FBX emitter to **extend** into a skinned emitter (add
  `LimbNode`/`Root` bone nodes + `Skin`/`Cluster` Deformers + bind Transforms; today it types the
  node `"Mesh"` to stay static). *Spec the exact `Indexes`/`Weights`/`TransformLink` layout against
  the engine's `FbxAsciiReader` / `FbxDeformer.GetWeights` before writing it.*
- **`ff9mapkit/battle/extract.py`** — the UnityPy `p0data` mesh-read recipe (`_decode_mesh`, packed
  `m_VertexData`, the winding gotcha) — the read backbone for the exporter.
- **`ff9mapkit/world/mesh.py`** — precedent that raw-geometry IO + loose-override deploy is a solved
  kit pattern (and the world-side geometry entry point for Phase 5).
- **Engine (reuse verbatim):** `ModelFactory.CreateModel` (universal load-instead-of-bundle seam),
  `ModelImporter.CreateCustomModelFromFbx` (full skinned importer), `AnimationClipReader` (JSON/binary
  `.anim` round-trip + `ParseToJSON` writer), `AnimationFactory` (name-based clip attach, disc-first),
  `AssetManager.SearchAssetOnDisc` (mod-folder resolution), the in-engine **ModelViewer** (browse GEOs
  by category + "Export anim") as a manual sanity tool.
- **Kit name/anim knowledge:** `_modeldb.py` (GEO id↔name), `catalog.py` (model→anim join, same
  `ANH_` key the engine uses), `archetypes.py` + InfoHub (place-by-name via `SetModel`),
  `playerswap.py` (the existing repoint-rig bridge).
- **Blender add-on** (`ff9mapkit/blender/`) — extend with Import/Export FF9 Model operators for the
  Phase 3 edit loop.
- **Provenance pattern** — extract from the user's install at runtime, write to their disk, gitignore
  `*.fbx`/`*.anim`/textures, ship zero SE bytes.

---

## 10. Load-bearing evidence index (source `file:line`)

| Fact | Evidence |
|---|---|
| Loose-FBX checked before bundle, no isBattle gate | `ModelFactory.cs:56-71` |
| GEO name → `Models/{type}/{geoId}/{geoId}` path | `ModelFactory.cs:34` |
| `ModelType` enum order (main=2, npc=4, sub=5…) | `Global/Model/ModelType.cs` |
| Skinned importer (skeleton, boneWeights, bindposes, `bone###`, `Animation`) | `ModelImporter.cs:59, 96, 132, 338, 387-398` |
| Root-bone / non-uniform-scale TODO (fidelity risk) | `ModelImporter.cs:111` |
| Bundled prefab already has SkinnedMeshRenderers | `ModelFactory.cs:123` |
| Field/character callers of CreateModel | `updateModelsToBeAdded.cs:25`, `DoEventCode.cs:1060`, `FieldMap.cs:482` |
| Anim = legacy clip, engine-sampled single pose | `btl_mot.cs:221-233`, `fldchar.cs:271-282`, `GeoAnim.cs:23-38` |
| Curves bind to bones by name; no count/order req | `AnimationClipReader.cs:120, 224-239`; `AnimationFactory.cs:68-101` |
| Custom `.anim` loose-loads (JSON/binary) | `AssetManager.cs:24, 421-423`; `AnimationClipReader.cs` |
| FBX read+write library present | `Memoria/Assets/3DModel/FbxIO.cs`, `Fbx{Ascii,Binary}{Reader,Writer}.cs` |
| Importer subsystem is in the shipping build | Memoria commit `9732e30e "FBX model importer (#991)"` (ancestor of `6b8bb2d5`) |
| World actors use the same factory/format | `updateModelsToBeAdded.cs` (gMode 1/3/battle), `WMActor.cs` |
| ≤4 bone influences per vertex (lossy cap) | `FbxSkeleton.RegisterWeight` |

**Unsettled until the human playtests:** (a) rigged-field-FBX round-trip fidelity (deform + stock
clip binding), (b) custom `.anim` loose-load on the field spawn path, (c) that no real GEO exceeds 4
bone-weights/vertex.
