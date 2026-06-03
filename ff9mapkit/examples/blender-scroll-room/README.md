# Fresh scrolling room in Blender — clean-start checklist

The hard-won lesson: **a re-used `.blend` can carry a camera posed by an older add-on version**,
which silently mis-scales. So always start a scrolling room from a **new** `.blend` and **Pose the
camera fresh**. This checklist is the known-good path (add-on **v0.4.5+**).

## 0. One-time
```
py ff9mapkit/blender/build_addon.py          # -> dist/ff9mapkit_blender-0.4.5.zip
py -m pip install -e ff9mapkit               # so `py -m ff9mapkit build ...` works anywhere
```
In Blender: **Edit ▸ Preferences ▸ Get Extensions ▸ ▾ ▸ Install from Disk…** → pick the 0.4.5 zip →
make sure **FF9 Map Kit** is enabled. (If an older version was installed, remove it first.)

## 1. New file
**File ▸ New ▸ General.** Delete the default cube. **Save it** somewhere (e.g.
`my_scroll_room.blend`) — saving makes the export land next to it.

## 2. Camera (FF9 Map Kit panel, press **N** in the 3D view)
- **Pitch 40**, **Distance 4500**, **FOV 42.2** (the proven sweet spot).
- Tick **Scrolling room**; **Canvas W 768**, **Canvas H 448** (a 2×-wide painting).
- **Setup FF9 Scene**, then **Pose Camera from Pitch/FOV**.
- **Sanity check:** the readout should say **FF9: pitch ~40 deg, FOV ~75 deg**. The **~75** (not 42)
  confirms v0.4.5 is showing the backdrop at the true in-game scale. If it says ~42, your add-on is
  stale — reinstall.

## 3. Paint guide → paint
- **Compute Paint Guide** (viewport grid + height wireframe) and **Export Paint Template** (writes
  `paint_template.png`, 3072×1792, with floor outline + vertical height guides).
- **(You)** paint your scene over the template: floor inside the outline, walls up the height
  guides, across the **full width**. Save as `back.png` (RGBA). Optional `front.png` (foreground
  occluder, mostly transparent).

## 4. Load art + walkmesh
- **Background Art ▸ Add Layer** → pick `back.png`; again for `front.png` (it gets a small z).
- **Reset Walkmesh to Floor** — this drops a walkmesh that **fills the floor at the correct scale**
  (no manual sizing). Reshape it if you want, but **Tab back to Object Mode before exporting**
  (Edit-Mode edits only flush on leaving Edit Mode).

## 5. Content (optional) + Export
- **Content:** drop NPC / Gateway / Spawn markers; set their props.
- **Export Field** (in **Object Mode**). Note the "Export to" folder shown at the bottom.
- Send me the folder path → I run `py -m ff9mapkit build … ` + deploy to field 4003.

## What we're confirming in-game (the two values that matter)
1. **Walkmesh fills the floor** — you can walk to the painted floor edges (validates the v0.4.5
   preview-scale fix end-to-end).
2. **The player plants on the floor** — feet sit on the surface, not floating/sunk (validates
   `character_offset = 298` for this camera; we re-tune it if the player is off).

Plus the freebies: the view **scrolls** across the full width, and `front.png` **occludes** the player.
