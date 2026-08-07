# 11 — Transplant your own model onto a summon (Blender round-trip)

```toml
[tutorial]
track = "D"
goal = "Wear a stock summon's real bones and camera with your own model."
requires = ["game", "blender"]
```

Wear a stock FF9 summon's real cast — its live bones, its native camera, its damage timing — with
your **own** model, instead of the donor creature. This is the experimental, engine-adjacent
sibling of tutorial 10 (character models): same round-trip shape (export → edit in Blender →
bring it back), a different, higher-stakes payload. Design notes + the full key reference:
[SUMMONS.md](../SUMMONS.md) / [FORMAT.md — `[[summon]]`](../FORMAT.md#summon-optional-repeatable).

**Prerequisites:** the kit set up with UnityPy; Blender 4.2+; the FF9 install. For the **hybrid**
lane (recommended, real motion) you also need the custom `memoria-patches` engine bundle built
with the s58 `SfxHybridDrive` feature — `summon-deploy --arm` will refuse otherwise. The
**overlay** lane needs nothing but stock Memoria; see the lane table in [SUMMONS.md](../SUMMONS.md#the-two-lanes)
before you start skinning.

## 1. Export the rig reference

```powershell
ff9mapkit summon-rig-ref ef227.bytes --out C:/gd/SCRATCH/summon-transplant/bahamut_rig.glb
```

This is a **skeleton only** — `bone000..bone09N`, no mesh, no clips — the armature to skin your
own mesh onto. Like `summon-export`/`summon-rig-ref` in general, the output is **local-only by
design**: a stock summon's rig is still Square-Enix-derived, so the command refuses to write into
the repo, a mod folder, or the FF9 install (no `--force`). If you want to *see* the donor's motion
while you work (to judge silhouette/scale, not to copy its geometry), also pull the full creature:

```powershell
ff9mapkit summon-export ef227.bytes --out C:/gd/SCRATCH/summon-transplant/bahamut_full.glb --anims all
```

That one is **textured**: the creature's own texture pages and palettes are decoded and embedded as
one PNG per material part (Bahamut: 6), so what opens in Blender is the dragon as the game draws it
— useful for judging your own art against the donor's. Pass `--no-textures` for geometry + rig only.
The decoded pixels are stock content like the rest of the export: same local-only rule, no `--force`.

## 2. Skin your mesh in Blender

Open `bahamut_rig.glb`. Skin your mesh onto its armature. Three rules carry the whole transplant;
breaking any of them is a hard error at import time, not a subtle bug later:

- **Keep the bone names and hierarchy exactly.** `bone000..bone09N`, same parent tree
  `summon-rig-ref` exported. Unity binds an `AnimationClip`'s curves by **hierarchy path**, so a
  renamed or reparented bone silently stops receiving the donor's motion.
- **Smooth (multi-bone) weights are fine for your mesh.** The donor creature itself is rigid —
  exactly one bone per vertex, FF9's own convention — but that's a property of *their* mesh, not a
  constraint on yours: the engine's skin math (`world_v = boneWorld[k]·inverseBind[k]·v`) doesn't
  care how many bones influence a vertex.
- **Bind-pose-is-the-fit-pose.** Whichever pose the armature is in *when you skin* becomes the pose
  your mesh renders **whole** at — the hybrid drive writes each bone's *absolute* world matrix
  every frame, and Unity's skin math cancels out exactly at the bind pose. `summon-rig-ref`
  ships the rig at the **identity rest** by default (`--rest identity`) — for most donors this
  already *is* their neutral pose (verify against `bahamut_full.glb`'s own clip-0/frame-0
  silhouette before assuming otherwise). Bind at rest unless you deliberately want your model to
  read "whole" mid-flight instead of standing still.

Texture note: keep material texture paths as **bare filenames** (e.g. `Thomas_d.png`, no folder) —
the deployed FBX resolves textures relative to its own folder, and a bare name is what
`summon-import`/`summon-deploy` validate for (they also accept an explicit `--textures` list if
your PNGs don't sit next to the model file).

**The raw-unit export.** `summon-rig-ref`/`summon-export` emit their `.glb` at the same
Blender-friendly `DEFAULT_SCALE = 0.01` every ordinary model export uses (FF9's hundreds-of-units
models → a few metres) — good for working in Blender, wrong for the engine, which reads FBX
vertex/bind data as **raw FF9 units** verbatim. The kit's ordinary model round-trip
(`model-gltf`/`model-import`) already closes this gap for you: the exported `.glb` carries a scale
stamp, and the return trip reads it back out with no extra flags (`docs/CUSTOM_MODELS.md`).
`summon-import` follows the same convention (`--scale`, default `0.01` — the `summon-rig-ref`
export scale, `models/gltf.py:DEFAULT_SCALE`); if your Blender export ever comes back the wrong
size in-game, that's the flag to check.

## 3. Bring it back — `summon-import`

```powershell
ff9mapkit summon-import thomas_skinned.glb --donor 227 --lane hybrid --mod-folder FF9CustomMap
```

Accepts either a Blender `.glb`/`.gltf` (converted through the model pillar's glTF importer) or a
ready `.fbx` (validated + deployed as-is). Validates the bone hierarchy against `summon-rig-ref`'s
own parent table (a mismatch is a hard error — see the rules above) and stages your model at
`Models/<type>/<id>/<id>.fbx` in the given mod folder. **Hybrid lane:** that's the whole model
deploy — no clips, the drive supplies all motion from the live donor bones. **Overlay lane:** it
additionally exports the donor's decoded clips as `.anim` (the kit's existing
`models/anim.py:clip_to_anim_json` writer — no new clip format) plus the `.sfxmodel` manifest and
`FileList.txt` that reference them. `--dry-run` stages everything under a SCRATCH mirror instead of
touching the live mod folder. Every deploy writes a self-contained `revert_summon_<id>.py`.

## 4. Author the `[[summon]]` block

```toml
[[summon]]
donor = 227                    # Bahamut
model = "thomas_skinned.glb"
lane  = "hybrid"                # or "overlay" for a DLL-free build
```

`ff9mapkit build`/`lint` validate this block (bad lane, a `private_ef` that collides with the
donor, an unresolvable `donor`, a missing model file, etc. are all caught offline) and print the
cast-trigger reminder below — `--from-toml your_field.toml` on either CLI verb reads the block
straight out of the file instead of repeating its keys as flags. Building the field itself only
*validates* this block; step 3 (`summon-import`) or step 5 (`summon-deploy`) is what actually
stages the model/`.seq`/DictionaryPatch line.

Point your summoning ability's `vfx1` at the block's `private_ef` id (the deploy verbs print which
id they picked, or set one yourself) — this is the ordinary `authoring-ff9-battles` step, not
something `[[summon]]` does for you.

## 5. Arm the hybrid lane (hybrid only) and cast

```powershell
ff9mapkit summon-deploy --from-toml my_field.toml --arm
```

Does the asset deploy (rows 1/1b/2 — same as step 3) and, because `--arm` is present, writes/
updates `Memoria.ini [SfxHybrid]` — backed up first, diff printed — **after** confirming the
deployed engine actually contains the s58 `SfxHybridDrive` feature (a stock engine gets a clear
refusal, not a silent no-op). Omit `--arm` to stage the assets and print the `[SfxHybrid]` block
without writing it — the confirm-first shape every engine-config mutation in this kit uses.
Arming is the one relaunch-gated step; the model/`.seq` themselves are recast-only (~ → Reload
field, or a fresh cast, picks them up with no relaunch). After the arm: relaunch once, cast the
ability, and watch your model fly the donor's real cast. Overlay-lane builds skip the arm entirely
— nothing to arm on a stock engine.

## Design-risk flag — read before you invest hours in skinning

A mesh can pose **perfectly** — every bone lands exactly where the donor's bone lands — and still
**look wrong**, because your silhouette and the donor's silently disagree (a boxy vehicle's flat
panels riding a dragon's flex; a two-legged biped riding a four-legged gait). This is a judgment
call the kit cannot make for you. Before committing to final art, scrub your retarget against the
full donor clip set (`summon-export --anims all` from step 1) and picture your mesh moving through
each one.

## Lane choice, at a glance

| | hybrid (default) | overlay |
|---|---|---|
| Motion | the donor's real live bones | the donor's motion, decoded once to `.anim` clips in your mod folder |
| Camera / big staging (fly-by, scale sweep) | inherited for free | needs `staging = "donor"` (nest the donor cast) or hand-authored curves |
| Engine | custom `memoria-patches` build (s58) required | stock Memoria |
| Fidelity | the proven ceiling — real articulation + real camera | flapping motion only unless you also supply staging |

## Provenance, one more time

Everything a stock summon's own bytes touch stays local (`summon-export`/`summon-rig-ref` refuse
any path under the repo, a mod folder, or the install — no `--force`). Your own retargeted model,
and everything `summon-import`/`summon-deploy` stage from it, land in **your own** mod folder and
are yours — the same footing as any other verbatim-fork carry.

## Command map

| step | command |
|---|---|
| rig only (to skin) | `summon-rig-ref` |
| rig + mesh + clips (to preview the donor's motion) | `summon-export` |
| validate the `[[summon]]` block | `ff9mapkit build`/`lint` (`content/summon.py`) |
| bring your retarget back | `summon-import` |
| deploy assets + arm the hybrid engine feature | `summon-deploy [--arm]` |
| wire the cast trigger | an ordinary `vfx1` on the summoning ability (`authoring-ff9-battles`) |
