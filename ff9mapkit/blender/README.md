# FF9 Map Kit — Blender add-on

Visually author a custom FF9 field's **camera** and **walkmesh** in Blender's 3D viewport, then
one-click export the pieces the [`ff9mapkit`](../README.md) CLI compiles into a Memoria mod. The
add-on is a front-end for the **spatial** layer: it produces `camera.bgx` + `walkmesh.obj` + a
`<name>.scene.toml` (placement) and scaffolds a `<name>.field.toml` (your logic — dialogue, story,
events) once; `ff9mapkit build` merges them. Scripts live in text, not Blender.

Targets **Blender 4.2+ / 5.x**.

## Install

```bash
python build_addon.py        # -> dist/ff9mapkit_blender-0.9.3.zip
```

Then install it as an **extension** (the Blender 4.2+/5.x way — the zip is an extension with
`blender_manifest.toml` at its root):

> **Edit → Preferences → Get Extensions → ▾ (top-right) → Install from Disk…** → pick the zip.
> (Or just **drag-and-drop the zip onto the Blender window**.) Then make sure **FF9 Map Kit** is
> enabled in the list.

A **FF9 Map Kit** tab then appears in the 3D viewport sidebar (press **N** to open it).

> Note: use **Get Extensions → Install from Disk**, *not* the legacy *Add-ons → Install from
> Disk* — on 5.1 the legacy path reports “Modules Installed ()” and nothing appears, because
> this is an extension (manifest-based), not a legacy `bl_info`-only add-on.

You'll also want the CLI for the final build step: `pip install -e ..` (the `ff9mapkit` package).
If the `ff9mapkit` command isn't found afterward (its Scripts dir isn't on PATH), use
**`py -m ff9mapkit build …`** instead — it works from any folder once the package is installed.

> **Export folder:** the *Export to* field defaults to `ff9field`, written **next to your saved
> `.blend`** (or `~/ff9field` if the .blend is unsaved). You can type an absolute path or browse to
> one. The export operator reports the exact folder it wrote to in the status bar.

## Workflow

The **FF9 Map Kit** sidebar panel walks top-to-bottom: **Setup → Camera → Walkmesh →
Background Art → Content → Export**. A typical pass:

1. **Setup FF9 Scene** — creates an FF9-posed camera and a flat `FF9_Walkmesh` plane on **z = 0**
   (FF9's floor is y=0, which maps to Blender's z=0). Press **Home** to frame it.
2. **Pose the camera** (*Camera* box) — set Pitch / Distance / FOV and hit *Pose Camera*, or just
   move/aim the camera freely. The panel shows the derived **FF9 pitch + FOV** live, and warns
   (advisory) if the pitch leaves the validated range — see below. For a **larger-than-screen
   scrolling room**, tick **Scrolling room** and set **Canvas W/H** (e.g. `768 × 448` = 2× wide);
   the FOV stays measured at the 384 screen, so the painting just gets wider — see *Scrolling rooms*
   below.
3. **Get a paint guide** (*Walkmesh* box) — two complementary aids for the current camera:
   - *Compute Paint Guide* reports where the floor edges + your walkmesh land on the painted canvas,
     writes `guide.txt`, and draws a reference floor grid **plus vertical height guides** (poles at
     the floor edges + a ceiling box) in the viewport — so you can model/paint walls in perspective.
   - *Export Paint Template* writes a transparent `paint_template.png` (floor outline + perspective
     grid + height guides) to trace over — paint your room on layers *under* it. It sizes to the
     **full painting** (so a scrolling room gets a wide template).
4. **(Human) paint the background layers** to that guide/template. Typical layers back-to-front: a
   **back** layer (everything behind the player), a **floor** layer, and optionally a **front**
   layer with a small `z` so it draws *over* the player (occlusion). Save PNGs (RGBA) — see the
   notes below.
5. **Load the art to model against** (*Background Art* box) — *Add Layer* loads a painted PNG as a
   camera background image and records it in the field's `[[layers]]`; *Clear* removes them. Smaller
   `z` previews in **front** (occlusion check), larger behind. View through the FF9 camera
   (Numpad 0) so the backdrop lines up with the frame.
6. **Model the walkmesh** — edit `FF9_Walkmesh` (stay on z=0 for a flat floor) into the walkable
   area, against the loaded backdrop. Keep it selected in the **Walkmesh** field. If you re-pose the
   camera, *Reset Walkmesh to Floor* snaps it back to a flat quad on the new floor frame to start
   over.
7. **Place content (optional)** — in the **Content** box (NPC / Gateway / Spawn buttons drop markers
   at the 3D cursor on the floor; select a marker to edit its props inline in the panel):
   - *NPC* drops an Empty (`FF9_NPC`). Move it where the NPC stands; set its model + line via
     `ff9_preset` (e.g. `vivi`) and `ff9_dialogue` (also editable in **Object Properties → Custom
     Properties**). For a non-preset model, delete `ff9_preset` and add `ff9_model` / `ff9_animset`
     / `ff9_anims` in the TOML after export.
   - *Gateway* drops a wire quad (`FF9_Gateway`) — move/scale it over the exit on the floor, and set
     `ff9_to` (destination field id) + `ff9_entrance`. The player walks out across the quad's first
     edge, so orient that edge toward where they should step out.
   - *Event* drops an amber wire quad (`FF9_Event`) — a walk-in trigger for chests / levers / story
     events. Move/scale it over the trigger spot; set `ff9_message`, `ff9_set_flag` (-1 = none),
     `ff9_once` inline (or flesh out the actions — give_item/gil/requires_flag — in the editor).
   - *Spawn* places the single `FF9_Spawn` marker — where the player appears on entry.
   - *Waypoint* drops a named point (`FF9_Waypoint`) — set `ff9_name`, then reference it from a
     cutscene by name (`walk = "<name>"` / `path = ["a", "b"]`) instead of typing coordinates. (A
     plain `walk` auto-routes around obstacles; waypoints are for forcing an exact route.)
   Markers are read on export; their floor positions are taken from where you place them.
8b. **Multi-camera (optional)** — for a field that cuts between camera angles as you walk (FF9
   streets/plazas). In the **Camera** box, **Add Camera** drops another FF9 camera (set its own
   *Yaw/Pitch/FOV* + *Pose*; select a camera to edit it). Give each camera its own painted
   background via **Add Layer**, then set that layer's **cam** index in the layer row. In **Content**,
   **Cam Zone** drops a blue zone — set `ff9_to_camera` (which camera to switch to) and place it over
   that camera's area; **zones must not overlap**. Export emits a `[[camera]]` array (camera 0 =
   default at load), per-layer `camera`, and `[[camera_zone]]` switches.
8. **Export Field** (*Export* box) — set the field `id` / `name` / `area` / `text_block` and the
   *Export to* folder, then *Export Field* writes `camera.bgx`, `walkmesh.obj`, the painted PNGs, and
   **two TOMLs** (Godot-style — placement vs. script):
   - `<name>.scene.toml` — the **spatial** layer (camera, walkmesh, layers, spawn, and each marker's
     position/zone by name). **Overwritten every export**, so re-export freely.
   - `<name>.field.toml` — the **logic** layer (`[field]` + per-entity dialogue/conditions + events).
     Written **only the first time** (a scaffold from your markers); after that it's *yours* and
     Export never touches it. Edit dialogue, story flags, and events here in a text editor.
9. **Build** — `ff9mapkit build <name>.field.toml --out <game>/FF9CustomMap` — it auto-merges the
   sibling `<name>.scene.toml` by entity name (scene = where, field = what). Then play.

## Fork an existing FF9 field (Import)

Instead of starting from a blank plane, **Import Field** loads a project produced by
`ff9mapkit import <field> --out <folder>` (run the CLI first). Two flavours:

- **BG-borrow** (`ff9mapkit import …`) — the engine renders the *real* field's art + walkmesh +
  camera; you only place NPC/gateway/spawn markers on top. The panel shows *forked from … (BG-borrow)*.
  Export writes a borrow `field.toml` (no scene/art — it can't be repainted).
- **Editable fork** (`ff9mapkit import … --editable`) — a full **custom scene** over the real field:
  the real camera, the walkmesh, and the background split into **one layer per depth** (occlusion +
  light/shadow shaders preserved). The panel shows *editable fork (custom scene)*. Import poses the
  exact camera, loads the per-depth art as the camera backdrop, and builds the real (multi-floor,
  color-coded) walkmesh to model against. Now you can:
  - **reshape the walkmesh** (move/add verts within a floor; for a multi-floor field, leave the
    cross-floor seam edges where they are — they're re-attached by world position on build),
  - **repaint any `layer_*.png`** (a single depth) without touching the others,
  - **place content**, then **Export Field**.

  Export preserves the exact `camera.bgx`, re-writes `walkmesh.obj` from your edits, and emits a
  `field.toml` with `[walkmesh] obj + frame = "world"` (and `+ links` for a multi-floor field, so a
  reshape stays connected) — **no character offset** (a forked real field is already in the engine
  frame). `ff9mapkit build` it exactly as above. This matches the CLI `import --editable` output, so
  a Blender re-export and a CLI build produce the same field.

## Scrolling rooms (larger-than-screen)

Tick **Scrolling room** in the *Camera* box and set **Canvas W/H** (e.g. `768 × 448` = 2× wide).
Then author exactly as above — the add-on handles the difference:

- the camera keeps its normal focal length (the FOV is measured at the 384 screen; only the painting
  gets wider), posed with the scroll bounds baked in;
- the floor guide + paint template **fill the wide canvas** and the walkmesh starts spanning it;
- *Export Field* writes a wide-`Range` `camera.bgx` and adds `[camera.scroll] enabled = true`, so
  `ff9mapkit build` injects the engine's `EnableCameraServices` and Memoria pans the view to follow
  the player.

Paint the full-width canvas (content along the whole length so scrolling reveals it). Runs on stock
Memoria. See the CLI worked example `../examples/scroll-demo/`.

## Two things to know

- **The Blender render is a placement aid, not a pixel-exact preview.** FF9 uses a slightly
  non-square vertical scale (14/15) that Blender's square-pixel render doesn't show. The exported
  **camera is exact** (the math bakes that in), and the **paint guide** (`guide.txt` /
  *Compute Paint Guide*) is the source of truth for aligning your art.
- **Supported pitch range (advisory).** The in-game camera is exact at any angle, but the paint
  guide's back-edge prediction is calibrated for the real FF9 downward-pitch range (~0–50°, the
  steepest shipped camera is ~49.6°). Past that the far/back edge of the guide can drift — the
  panel warns but never blocks. For a dead-on back edge at a steeper angle, re-pin the vertical
  canvas scale with one in-game grid check (see `project-ff9-camera-math`).

## How it's built / trusted

The Blender↔FF9 camera + coordinate conversion lives in a **bpy-free `bridge.py`**, validated
offline (`tests/`): all 6 real FF9 cameras round-trip through Blender params and back within 1
unit, and an end-to-end dry run feeds a bridged camera + mesh straight through `ff9mapkit build`.
The `bpy` UI layer is a thin wrapper over that validated core.
