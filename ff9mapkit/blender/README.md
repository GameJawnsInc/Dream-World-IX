# FF9 Map Kit — Blender add-on

Visually author a custom FF9 field's **camera** and **walkmesh** in Blender's 3D viewport, then
one-click export the pieces the [`ff9mapkit`](../README.md) CLI compiles into a Memoria mod. The
add-on is a front-end: it produces `camera.bgx` + `walkmesh.obj` + a `field.toml`; `ff9mapkit
build` does the rest.

Targets **Blender 4.2+ / 5.x**.

## Install

```bash
python build_addon.py        # -> dist/ff9mapkit_blender-0.1.0.zip
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

## Workflow

1. **Setup FF9 Scene** — creates an FF9-posed camera and a flat `FF9_Walkmesh` plane on **z = 0**
   (FF9's floor is y=0, which maps to Blender's z=0).
2. **Pose the camera** — set Pitch / Distance / FOV and hit *Pose Camera*, or just move/aim the
   camera freely. The panel shows the derived **FF9 pitch + FOV** live, and warns (advisory) if the
   pitch leaves the validated range — see below.
3. **Model the walkmesh** — edit `FF9_Walkmesh` (stay on z=0 for a flat floor) into the walkable
   area. Keep it the object selected in the **Walkmesh** field.
4. **Compute Paint Guide** — reports where the floor edges + your walkmesh land on the 384×448
   painted canvas and writes `guide.txt`. Paint your background layers to match those coordinates.
5. **Export Field** — writes `camera.bgx`, `walkmesh.obj`, and `<name>.field.toml` to the export
   folder. Drop your painted PNGs next to it and fill in `[[layers]]` / `[[npc]]` / `[[gateway]]`.
6. **Build** — `ff9mapkit build <name>.field.toml --out <game>/FF9CustomMap` (see the main docs),
   then play.

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
