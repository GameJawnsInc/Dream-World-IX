# 12 — Create a creature from scratch

Author a **wholly-original creature** — its mesh, rig, weights, texture, and animation all yours,
zero FF9-derived bytes — and place it in a field as a talking, idling NPC. All of it runs on
**stock Memoria** (loose-FBX loader + loose `.anim` clips + DictionaryPatch registrations).

The worked example is [`examples/boletta/`](../../examples/boletta/) — Boletta, a knee-high
mushroom sprite, in-game proven. This page walks her pipeline; the same steps carry any creature.

**Prerequisites:** the kit set up with UnityPy. If you'd rather sculpt in Blender than write
geometry in Python, see the alternative in §6 — the mint + animset steps are identical.

## 1. Build the model as data

A model is just the kit's Model struct: bones, one mesh (verts / normals / per-vertex UVs /
triangles / weights), a material, a texture image. `make_creature.py` generates Boletta's
procedurally and hands the struct to the same emitter every model edit uses:

```powershell
py ff9mapkit/examples/boletta/make_creature.py        # paths from a repo checkout's root
```

Rules that apply to **any** from-scratch model (all encoded in the example's comments):

- **Model space is the engine's:** Y-DOWN (ground at `y=0`, head at the most-negative `y`),
  FF9 units — a knee-high critter is ~300 tall, adult characters ~400-500.
- **Bones are `bone000…boneNNN`** with `bone000` the root, authored at rest; ≤4 weights per
  vertex. Animations bind by these names.
- **One merged mesh.** A tiny standalone renderer can be one-shot disabled by the field's
  character-show pass — fold every part into a single mesh.
- **Calibrate, don't assume.** Triangle winding is measured from a real model
  (`calibrate_winding`; FF9's cutout materials can cull backfaces), and texture-V orientation is
  checked by eye: the struct's `v=0` is the image **bottom**, so a strip's image-top rows must map
  to the model's top.
- **Look before you deploy.** `preview.render_model(struct)` software-renders the struct — the
  example writes `boletta_preview_*.png`. If the previewer shows it, the geometry, UVs, and
  texture are coherent; what remains for the game is the FBX import and skinning.

The emitter (`emit_skinned_fbx`) self-validates against a port of the engine's FBX tokenizer — a
malformed FBX cannot reach disk.

## 2. Mint the model id

The creature ships as a `[[mint]]` with the `fbx=` form — a brand-new GEO id (band ≥ 6000) with a
novel name whose GROUP sets the model type and path:

```toml
[[mint]]
id = 6300
name = "GEO_NPC_F1_M300"
fbx = "creature/6300.fbx"     # the generator's output; adjacent PNGs ship automatically
```

Deploy the field once now (step 3 needs the mint's `3DModel` line registered):

```powershell
py tools/deploy_field.py ff9mapkit/examples/boletta/boletta.field.toml
```

## 3. Author its animset

Field NPCs need at least a `stand` clip. `make_creature_anims.py` builds Boletta's idle from
curves (`new_clip`) and mints it onto her id (`deploy_new_anim`):

```powershell
py ff9mapkit/examples/boletta/make_creature_anims.py "C:\...\FINAL FANTASY IX\FF9CustomMap"
# -> clip ANH_NPC_F1_M300_IDLE key 60001
```

What the kit handles for you, and why it matters:

- **Field anim keys are 16-bit** end to end (.eb args + engine actor slots are u16) — keys mint in
  the **60000–65535** band. A larger key silently truncates and the clip never attaches.
- **The whole skeleton gets keyed**: unkeyed bones are filled with static rest-pose channels, like
  every real FF9 clip. (Playback only resets keyed bones, and the engine composes its head-focus
  look offset onto the neck every frame — an unkeyed neck accumulates it into a spinning head.)
- **Position curves replace `localPosition`** — carry the bone's rest offset in the curve.
- The clip lands in `Animations/<mintId>/<key>.anim` and registers via a `3DModelAnimation` line.

## 4. Place it

```toml
[[npc]]
name = "Boletta"
model = 6300
pos = [-220, -350]
speaker = "Boletta"           # the dialogue-window name tag (`name` is only the object name)
dialogue = "Grew here all by myself!"
anims = { stand = 60001 }     # the key step 3 printed
```

Redeploy, **relaunch** (new `3DModel` + anim keys register at startup), F6 → warp to the field.

## 5. The deploy-revert caveat

`deploy_field` reverts the slot's prior deploy before applying the new one — DictionaryPatch lines
minted **between** deploys (your step-3 anim registration) get rolled back. **Re-run step 3 after
every redeploy of the field** (it's idempotent: same clip name → same key). Symptom if forgotten:
the creature stands frozen in rest pose after the next relaunch.

## 6. Blender instead of Python

Prefer sculpting? Export any model as a starting skeleton (`ff9mapkit model-gltf …`), replace the
geometry wholesale in Blender (keep the `bone###` armature), return it with
`ff9mapkit model-import … --id 6300` — then steps 2–4 are identical. New clips can come from a
Blender action too: `ff9mapkit model-anim-new <model> --glb yours.glb --action <name> --deploy <mod>`.

## Troubleshooting

| Symptom | Meaning |
|---|---|
| invisible + field hiccup | the FBX import was rejected — check `Memoria.log` (game root) for the importer exception |
| visible but frozen in rest pose | the clip didn't attach — anim key unregistered (see §5) or not 16-bit |
| only the head moves (spins) | no clip is sampling the skeleton — same as frozen, plus head-focus feedback |
| distorted / exploded geometry | skinning: weights reference wrong bone numbers, or verts not authored in rest space |
| renders in preview, invisible in game | winding/culling — re-check `calibrate_winding` ran against a real install |
