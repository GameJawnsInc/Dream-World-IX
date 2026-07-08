# 10 — Edit a character model in Blender

Round-trip a real FF9 model through Blender: export it (mesh, rig, textures, animations) as glTF,
edit it, and bring it back — either as an **override** of the original or as a **new minted model
id** that leaves the original untouched. All of it runs on **stock Memoria** (the engine's
loose-FBX model loader).

**Prerequisites:** the kit set up with UnityPy; Blender 4.2+. Design notes and limits:
[CUSTOM_MODELS.md](../CUSTOM_MODELS.md). The animation-editing half of this loop:
[ANIMATION_EDITING.md](../ANIMATION_EDITING.md).

## 1. Export to glTF

```powershell
ff9mapkit models vivi                              # find the GEO name / id
ff9mapkit model-gltf GEO_MAIN_F0_VIV --out vivi.glb
```

The `.glb` embeds the skinned mesh, the bone rig, textures, and a useful animation set
(`--anims all` for the model's whole clip folder; `--anims "idle talk"` for named actions). An
action whose clip lives in another model's animation folder — common for NPC variants, whose
idle/walk usually belong to the family's base model — is found there automatically (the CLI notes
which clips came from a donor folder). The `.glb` also carries a stamp (source id, scale) so the
return trip needs no extra flags.

Alternatively, in the Workspace: **Import** tab → **Custom 3D models** → **Export .glb…**; in
Blender: the add-on's **Import FF9 Model**.

## 2. Edit in Blender

Open the `.glb` (File → Import → glTF 2.0). Edit the mesh (sculpt, extrude, retexture) and/or the
animation keyframes. Constraints that keep the return trip valid:

- keep the **armature and bone names** (`bone###`) — animations bind by bone name;
- for a mesh-splice re-import, keep the **vertex count** compatible with the source;
- export with File → Export → glTF 2.0 including the armature.

## 3. Import back

```powershell
# override the original model in-game:
ff9mapkit model-import vivi_edited.glb --deploy FF9CustomMap

# or mint a NEW model id (>= 6000, clear of every real id) and leave the original untouched:
ff9mapkit model-mint GEO_MAIN_F0_VIV --id 6000 --deploy FF9CustomMap
ff9mapkit model-import vivi_edited.glb --id 6000 --deploy FF9CustomMap
```

`model-import` reads the glTF stamp to find the source rig and textures (`--like` forces a
different source), writes the loose-FBX override into `Models/<type>/<id>/` in the mod folder,
and by default also round-trips any **edited animation clips** as loose `.anim` overrides
(`--no-anims` for mesh only).

A minted id is a fresh `SetModel` target: place it in a field with `[[npc]] model = 6000`, or use
it as a custom playable character's battle model (`examples/thirteenth-character/`).

## 4. Verify

Deploy the mod folder (register it in `Memoria.ini` once) and launch. With the engine bundle:
**F6 → Go → Reload field** picks up a model override without relaunching ("Reload + anims" also
re-reads edited clips). The edited mesh renders wherever the model appears — field, battle, or
both, depending on the GEO type.

## Command map

| step | command |
|---|---|
| browse models | `models`, `catalog` |
| export | `model-gltf` (glTF, the edit loop) · `model-export` (raw FBX) |
| animations only | `model-anim` (dump/deploy loose `.anim` JSON) |
| new id | `model-mint` |
| return trip | `model-import` |
| custom-character animsets | `playable-anims` |
