# Editing FF9 animations in Blender — a basic tutorial

Edit a real FF9 character's animation (a walk, a run, an idle, a gesture) by hand in Blender and play it in
the game. DLL-free: a loose `.anim` you produce **shadows** the bundled clip. This walks through editing
Vivi's **run**; the same steps work for any model + clip.

> The division of labour (same as the field tools): the `ff9mapkit` CLI reads/writes the game's data; the
> Blender add-on only moves the `.glb` in and out. You run the CLI commands; Blender does the editing.

---

## 0. One-time: what you need

- The `ff9mapkit` CLI with the model commands (run `ff9mapkit model-gltf --help`; if it errors with
  `invalid choice`, your build predates them — use a checkout: `py -m ff9mapkit …` from the kit root).
- The Blender add-on installed (`blender/dist/ff9mapkit_blender-*.zip`) — optional but convenient; you can
  use plain **File ▸ Import/Export ▸ glTF 2.0** instead.
- Blender 4.2+.

---

## 1. Export the clip to a `.glb`

Bring **just the run** so there's one thing to edit (add `--anims auto` for idle/walk/run/turns, or `all`):

```
ff9mapkit model-gltf GEO_MAIN_F0_VIV --anims run --out vivi_run.glb
```

`GEO_MAIN_F0_VIV` is Vivi (id `8`). See names with `ff9mapkit models`. The `.glb` is rigged, textured, and
carries the clip as a Blender **Action** named `run`.

## 2. Import it

- **Add-on:** FF9 Map Kit sidebar (`N`) ▸ *3D Model* ▸ **Import Model** ▸ pick `vivi_run.glb`.
- **or** File ▸ Import ▸ glTF 2.0.

She comes in Y-up at ~0.01 scale (a few metres tall). You'll see the armature (`bone000…`) + her mesh parts.

## 3. Find the animation

1. Switch to the **Animation** workspace (top tabs) — you get a Dope Sheet + timeline.
2. Select the **armature** (click Vivi's bones/rig), then enter **Pose Mode** (Ctrl-Tab, or the mode dropdown).
3. In the Dope Sheet header, switch its mode to **Action Editor**. The Action dropdown should show **`run`**.
   Pick it if it isn't already active. You'll now see the keyframes (diamonds) along the timeline.
4. Press **Spacebar** to play — she runs in place. The frame range is the clip's own length (~17 frames).

## 4. Edit keyframes (the basics)

Everything below is done in **Pose Mode** with a **bone selected**.

**Move an existing pose**
1. Scrub the timeline to a frame that has a keyframe (a diamond in the Dope Sheet).
2. Click the bone you want to change (e.g. an arm — `bone024`/`bone025` on Vivi).
3. **Rotate** it: press `R` (optionally then `X`/`Y`/`Z` to constrain), move the mouse, click to confirm.
   (Grab `G` for position — but for characters you almost always rotate bones.)
4. Re-key it: press **`I` ▸ Rotation** (or **Whole Character** to key everything). The diamond updates.

**Add a keyframe at a new frame** — scrub to the frame, pose the bone, `I ▸ Rotation`.

**Faster: Auto-Key** — enable the **record dot** ⏺ next to the timeline play controls. Now any pose change
keys automatically; just scrub to a frame and rotate.

**Adjust timing** — in the Dope Sheet, box-select keyframes and `G` to slide them along time.

**Delete a keyframe** — select it in the Dope Sheet, press `X`.

Play it back (Spacebar) as you go. Small changes read clearly at edit speed even if they blur at run speed
in-game.

## 5. Export back + deploy

- **Add-on:** *3D Model* ▸ **Export Model** ▸ choose a save path (e.g. `vivi_run_edited.glb`). Optionally
  fill **Mod folder** (`…/FF9CustomMap`). It writes the `.glb` and **copies a command to your clipboard**.
- **or** File ▸ Export ▸ glTF 2.0 with **Format: glTF Binary (.glb)**, **+Y Up**, **Skinning** + **Animation**
  + **Custom Properties** all on, **Apply Modifiers OFF**.

Then run the copied command (or type it):

```
ff9mapkit model-import "vivi_run_edited.glb" --deploy "C:\...\FINAL FANTASY IX\FF9CustomMap"
```

It writes only the clips you actually **changed** as loose `.anim` overrides (untouched clips keep the
bundled version). It prints which clips it wrote.

## 6. Test in-game

**Relaunch FF9** (or use the F6 button below), then move Vivi so she runs. An animation change needs its
clip cache cleared: the engine caches loaded clips by file path (`AnimationClipReader.LoadedClips`) and a
plain field reload re-requests the same path, so it keeps the *cached* clip. Two ways to apply a re-deploy:

- **F6 ▸ Go ▸ "Reload + anims"** (fast) — clears the clip cache and reloads the field, so the new `.anim`
  shows without leaving the game. (Needs the shipped/updated engine bundle; plain **Reload field** keeps the
  cached clip on purpose, for when you only changed the mesh — which *does* refresh on a plain reload.)
- **Relaunch FF9** (always works).

Revert by deleting the written files under `FF9CustomMap\StreamingAssets\Assets\Resources\Animations\8\`.

---

## Rules & gotchas (the load-bearing ones)

- **Start from File ▸ New and import the model ONCE.** Importing into a scene that already has the model
  stacks duplicate actions (`run.001`, `run.002`, …). They all route to the same clip, collide, and
  *clobber each other last-wins* — so your edit can silently lose to a pristine copy. If Export writes far
  more clips than you edited, or the CLI prints `two animations map to key N — keeping the last-written`,
  that's this. (Export Model defaults to the **active action only**, which avoids it; a clean scene is still
  the real fix.)
- **A bone with only a couple of keyframes HOLDS that pose for the rest of the clip.** FF9 clips are ~0.5 s;
  two keys at frames 1–2 (~0.06 s) means the bone snaps there and holds for the remaining ~0.45 s = looks
  frozen. To change *part* of a motion, **keep the bone's existing keyframes** and modify only the ones you
  want (or Auto-Key and re-pose at those frames) — don't delete the rest of the curve. The export replaces a
  bone's whole curve with whatever keys you ship, so sparse keys = a held pose.
- **Never rename the `bone000…` bones.** The engine binds animation to bones **by name**; a renamed bone
  animates nothing.
- **Keep the Action name** (`run`, `walk`, `idle`, …) — or its numeric anim key. The exporter routes each
  clip back to the right slot by that name (a stamped key, with a name→key fallback). A clip renamed to
  something unrecognized is **skipped with a warning** (never silently, but it won't ship).
- **Only what you change ships.** Edit-detection compares your curves to the original and writes just the
  edited clips. It catches rotation changes down to ~0.16°, plus position **and scale** edits (squash/stretch
  works). An untouched round-trip writes nothing.
- **Interpolation:** the engine's JSON `.anim` reader uses smooth default tangents (it ignores per-key
  tangents), so a **Constant/stepped** F-curve will play as a glide, not a snap. Use dense keys for a hard
  hold. (This matches how the game's own tools save clips.)
- **Don't add bones** or a new mesh expecting the stock clips to drive them — animation editing edits the
  existing rig's motion. (New geometry is the mesh-edit loop; a new skeleton is out of scope.)
- **Scale/orientation:** leave the imported scale (~0.01) and **+Y up** as-is; the kit handles the
  FF9↔glTF conversion. Don't apply the armature or re-orient the whole rig. *(If you do move/scale/rotate the
  **Armature object**, import **refuses** it — FF9 can't carry a transform on the root bone — so either reset
  the Armature to identity or **Object ▸ Apply ▸ All Transforms** (Ctrl-A) to bake it into the bones + mesh.)*

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `invalid choice: 'model-gltf'` | Your `ff9mapkit` predates the model commands — use a checkout (`py -m ff9mapkit`) or an updated install. |
| Export said `no routable key … skipped` | You renamed the Action to something unrecognized. Rename it back to the clip label (`run`) or its numeric key. |
| `two animations map to key N`, or way more clips written than you edited | Duplicate actions from importing the model more than once. Start from **File ▸ New**, import once; keep Export Model's "Export ALL actions" **off**. |
| My edit didn't take / the run looks stock | Your edited clip lost the last-wins race to a pristine duplicate (see above), **or** the edited bone had too few keys and holds a pose. Clean scene + keep the bone's original keys. |
| "no changed clips to write" | Your edit was below the detection threshold, or you edited a different Action than the one exported. Re-check you edited the `run` Action. |
| Import: *"the object above bone000 … has a live transform"* | You moved / scaled / rotated the **Armature** object (FF9 can't carry a root-bone parent transform). Reset the Armature to identity, or **Object ▸ Apply ▸ All Transforms** (Ctrl-A), then re-export. |
| Change doesn't show in-game | F6 reload can keep a cached clip — **relaunch** FF9. Confirm the `.anim` landed under `Animations/8/`. |
| The `.anim` landed under a *different* `Animations/<N>/` than the model's id | Correct: many clips (especially NPC-variant idles/walks) live in a **donor** model's folder — the engine reads them from there, and the kit writes the override where the engine looks. Note a donor-folder clip is **shared**: the override affects every model that plays it (the import prints a warning naming the folder). |
| A limb animates nothing after editing | A bone got renamed (check for `bone024.001` etc.). Rename it back to `bone024`. |

---

Under the hood this is the same round-trip the CLI proves offline (`ff9mapkit model-anim` dumps/deploys the
raw JSON if you'd rather hand-edit numbers than use Blender). Deep notes: `docs/CUSTOM_MODELS.md` (Phase 2/3).
