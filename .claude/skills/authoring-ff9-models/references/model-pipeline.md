# Model pipeline — round-trips, mint bands, from-scratch

Distilled from memory `project-ff9-custom-models` (THE deep recipe — read it before nontrivial model
work) and `ff9mapkit/docs/CUSTOM_MODELS.md` (§0b implementation status, §10 evidence index). Quoted
lines below are verbatim from those sources; everything else is a pointer.

## Contents

- [Engine facts (why it is all DLL-free)](#engine-facts-why-it-is-all-dll-free)
- [Export / import / preview](#export--import--preview)
- [Reskin / deployed inventory](#reskin--deployed-inventory)
- [Mint bands](#mint-bands)
- [New clips (`model-anim-new`)](#new-clips-model-anim-new)
- [From-scratch pipeline](#from-scratch-pipeline)
- [Blender footguns](#blender-footguns)

## Engine facts (why it is all DLL-free)

- "**Import needs NO DLL.** `ModelFactory.CreateModel` (`Global/Model/ModelFactory.cs:56-71`) — the
  single choke point for field/battle/world models — probes the mod folder for a loose
  `Models/{typeInt}/{geoId}/{geoId}.fbx` BEFORE the bundle". Path root =
  `<modfolder>/StreamingAssets/Assets/Resources/`.
- "**Animations = stock Unity legacy `AnimationClip`, bound by bone NAME** (`bone{id:D3}`), no
  count/order requirement — only names must match".
- "**Custom `.anim` also loose-loads, no DLL.**" A loose clip at
  `<mod>/StreamingAssets/Assets/Resources/Animations/{geoId}/{key}.anim` shadows the bundled p0data5 clip.
- `ModelType` enum: "none=0, acc=1, **main=2, mon=3, npc=4, sub=5**, battle_weapon=6 (weapons →
  `BattleMap/BattleModel/6/...`)". Weapons live in **p0data2** and are STATIC meshes; the kit wraps a
  skeleton-less mesh in a trivial 1-bone rig so the whole skinned pipeline handles it unchanged.

## Export / import / preview

- `ff9mapkit model-export <GEO|id> [--out|--deploy MODFOLDER] [--flat]` — skinned FBX-ASCII + PNG
  textures in the engine override layout.
- `ff9mapkit model-gltf <model> [--anims auto|all|none|<list>] [--scale]` — a self-contained `.glb`
  Blender opens natively (skeleton + skin + textures + clips). "Blender reads only BINARY FBX, not
  ASCII" — the Blender edit loop goes through glTF, not FBX.
- `ff9mapkit model-import <edited.glb> [--like <GEO>] [--id N] --deploy MODFOLDER` — v1 `--like`
  keeps the source rig and splices in only the edited geometry; v2 (no `--like`) re-rigs fully. It
  auto-detects the source by mesh/node name and, when the vertex count changed, auto-falls back to a
  "HYBRID RE-RIG: keep the source's PRISTINE skeleton + id/type + and take the edited geometry +
  weights (by FF9 bone number) + embedded textures" — so `model-import <edited.glb> --deploy <mod>`
  works with zero flags.
- `ff9mapkit model-preview` — pure-PIL software render, "TRUE per-bone skinning posed at the stand
  clip's frame 0".
- Mesh GameObject NAMES are load-bearing (the Garnet `garnetShortHairTable` lesson): "the round-trip
  must PRESERVE original mesh GameObject names, not just geometry/weights — the engine has
  per-character name-keyed logic." Keep the reserved child names
  (long_hair/short_hair/field_model/battle_model/mesh0..N) unchanged in Blender.
- Story-evolved models: "an **OVERRIDE** (re-import at the real id/name) PRESERVES it for free; a
  **MINT** (new id ≥6000, novel name) BYPASSES it" — and "a story-evolved character is SEVERAL ids,
  not one" (editing one form leaves the others stock).

## Reskin / deployed inventory

- `model-reskin` — export textures / deploy edited PNGs. "ENGINE FACT from ModelFactory.cs:100-116:
  the checkTextureOnDisc probe swaps textures BY NAME for every bundle-loaded model; opt-outs =
  Zidane F3/F4/F5 + CustomModelField, warned". So "ANY bundled model can be texture-reskinned by
  name without a mesh — the cheapest edit."
- A weapon reskin = drop ONE PNG at `BattleMap/BattleModel/6/{id}/{id}.png` (texture name = the geoId).
- "battle models load on battle ENTRY (a menu reload won't hot-reload them → RELAUNCH to pick up a fresh loose
  override)".
- `model-deployed` — scan/revert a mod folder's loose model state (overrides / reskins / mints /
  anims / dangling directives).

## Mint bands

- GEO ids: "**Band**: real GEO ids are 0..5511 → mint band ≥ **6000** (SetModel id is 2-byte, max
  65535). NEVER reuse a real NAME (the value-reverse map would hijack the real model's GetGEOID
  path) — use a novel token."
- Registration: the "`3DModel <id> <GEO_NAME>` DictionaryPatch directive" adds the id at load — "a
  new id needs one relaunch". Declarative form: `[[mint]]` (`id` ≥6000 + `from="<GEO>"` re-export OR
  `fbx="<path>"` custom model; optional `name`/`anims_from`) auto-borrows the source's animset. CLI:
  `ff9mapkit model-mint <src> --id N [--name] [--deploy MODFOLDER|--out DIR]`.
- FIELD animation keys are 16-bit end to end: "**A field-playable anim key MUST fit UInt16
  (≤65535)**" (the `.eb` anim-setter args and the engine's `Actor.idle/walk/run/turnl/turnr` are
  u16). "**Mint band now 60000–65535** (stock AnimationDB tops out at 14739)". The 1M+ battle-animset
  band "works ONLY because battle `btl.mot[]` is Int32 — battle-only."

## New clips (`model-anim-new`)

- "**a NEW clip must key the FULL skeleton**" — `new_clip` fills unkeyed bones/channels with
  rest-pose curves. "Diagnostic signature — 'head spins continuously, body frozen' = nothing is
  sampling the skeleton + head-focus on."
- "**bone000 rest need not be identity**" — "a synthesized rotation must COMPOSE onto rest
  (`synth_spin_curves(rest=…)`, `q = yaw * rest`), not replace it."
- "**A minted ANH name must NOT equal a stock AnimationDB name**" — `deploy_new_anim` refuses
  stock-name collisions.
- "New keys register at STARTUP → relaunch per new key." For edited EXISTING clips, use the debug-menu
  **"Reload + anims"** button — a plain field reload serves the cached clip
  (`AnimationClipReader.LoadedClips`).
- Redeploy survival: `deploy_field`'s revert/re-apply "PRESERVES foreign DictionaryPatch lines
  (matches its own FieldScene/`3DModel`/`3DModelAnimation` by exact id/key, not GEO block)" — a
  between-deploy `model-anim-new` clip survives a field redeploy (`ff9mapkit/ff9mapkit/dictpatch.py`).
- Donor-folder redirect: "a clip's on-disc p0data5 folder is derived from the anim NAME's model
  tokens, NOT from the model playing it" — an edited donor clip must deploy to the DONOR's folder
  ("an override under the playing model's folder is silently DEAD"), and "a donor-folder override is
  SHARED by every model that plays the clip".

## From-scratch pipeline

- The proven loop: "struct→`emit_skinned_fbx`→`[[mint]] fbx=`→`model-anim-new`(minted
  id)→`[[npc]]`". Worked example: `ff9mapkit/examples/boletta/` (generator scripts + field.toml;
  scripts are the source of truth) + tutorial `ff9mapkit/docs/tutorials/12-creature-from-scratch.md`.
- "Two CALIBRATIONS that matter for any from-scratch model: (1) triangle WINDING derived empirically
  from a real model … don't assume; (2) texture-V orientation verified via `preview.render_model`".
- One merged mesh per model (the scrunchie lesson): "a tiny/single-bone/nested standalone mesh may
  silently frustum-drop on loose-FBX import even when the data is perfect — merge it into a
  same-texture sibling" (the kit's `merge_nested_child_meshes` does this at every engine-FBX emit).

## Blender footguns

Full tutorial + troubleshooting: `ff9mapkit/docs/ANIMATION_EDITING.md`. Headlines:

- Export the ACTIVE action only (the add-on defaults to it) — exporting all actions deploys pristine
  duplicates that clobber the edit, and phantom stand-clip overrides can render the model INVISIBLE.
- Import the model into a scene ONCE — re-imports stack duplicate `.001` actions that collide.
- A bone with only ~2 keyframes HOLDS that pose for the rest of the clip (the splice replaces the
  whole bone curve) — the top "arm stuck up" confusion.
