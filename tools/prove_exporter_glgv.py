#!/usr/bin/env python3
"""Prove the ff9mapkit EXPORTER in-game, WITH per-overlay occlusion.

Fork GLGV (rm1) as a full CUSTOM SCENE (NOT borrow):
  * walkmesh  -- RE-EXPORTED from the real .bgi via bgi.build (world frame, orgPos=0).
  * art       -- extract_layers(): one [[layers]] per DEPTH (not a flat composite), so the engine
                 redraws the depth-ordered scene and occlusion is preserved (foreground overlays
                 draw over the player) -- the "editable art" path.
  * camera    -- GLGV's real camera.bgx.
If the player walks the floor aligned with the art AND foreground pieces occlude him, the exporter +
multi-layer extract are engine-validated.

Run:  py tools/prove_exporter_glgv.py
then: py tools/deploy_field.py tools/scroll_out/glgv_exp/GLGV_EXP.field.toml
"""
import os
import shutil
import sys
from pathlib import Path

KIT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ff9mapkit"))
sys.path.insert(0, KIT)
from ff9mapkit import extract
from ff9mapkit.scene import bgi

FIELD = "glgv_map792_gv_rm1"
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "tools" / "scroll_out" / "glgv_import"
OUT = ROOT / "tools" / "scroll_out" / "glgv_exp"
OUT.mkdir(parents=True, exist_ok=True)

# 1) RE-EXPORT the walkmesh: import (world_verts) -> bgi.build (world frame, org=0) -> walkmesh.obj.
wm = bgi.BgiWalkmesh.from_bytes((SRC / "walkmesh.bgi").read_bytes())
wv = wm.world_verts()
faces = [tuple(t.vtx) for t in wm.tris]
floor_ids = [t.floor_ndx for t in wm.tris]
order = []
for f in floor_ids:
    if f not in order:
        order.append(f)
lines = ["# GLGV walkmesh RE-EXPORTED by ff9mapkit (world frame, org=0)"]
for (x, y, z) in wv:
    lines.append(f"v {x} {y} {z}")
if len(order) > 1:
    for fid in order:
        lines.append(f"o floor_{fid}")
        for (a, b, c), fl in zip(faces, floor_ids):
            if fl == fid:
                lines.append(f"f {a + 1} {b + 1} {c + 1}")
else:
    for (a, b, c) in faces:
        lines.append(f"f {a + 1} {b + 1} {c + 1}")
(OUT / "walkmesh.obj").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

# 2) EXTRACT the art as depth-ordered layers (preserves occlusion) + the real camera
shutil.copyfile(SRC / "camera.bgx", OUT / "camera.bgx")
info = extract.extract_layers(FIELD, OUT)
if info is None:
    sys.exit(f"{FIELD} not [Export] Field=1'd in-game yet -- no per-overlay PNGs on disk.")
layers = info["layers"]
print(f"layers: {len(layers)} depths {[L['z'] for L in layers]}  (skipped {info['skipped_blend_overlays']} blend overlays)")

# 3) custom-scene field.toml: real camera + re-exported walkmesh + per-depth art layers
spawn = (1430, -205)
layer_blocks = "\n".join(f'[[layers]]\nimage = "{L["image"]}"\nz = {L["z"]}' for L in layers)
toml = f"""# EXPORTER + MULTI-LAYER PROOF -- GLGV forked as a CUSTOM SCENE. Walkmesh re-exported via
# bgi.build (org=0); art split into one layer per depth so the engine preserves occlusion (the player
# is drawn over by foreground pieces and draws over the floor), exactly like the real field.
[field]
id = 4003
name = "GLGV_EXP"
area = 36
text_block = 1073

[camera]
borrow = "camera.bgx"
[camera.scroll]
enabled = true

[walkmesh]
obj = "walkmesh.obj"
frame = "world"

{layer_blocks}

[player]
spawn = [{spawn[0]}, {spawn[1]}]

[[npc]]
name = "Vivi"
preset = "vivi"
pos = [{spawn[0]}, {spawn[1] + 250}]
dialogue = "Re-exported walkmesh + layered art. If a wall hides me, occlusion survived."
"""
p = OUT / "GLGV_EXP.field.toml"
p.write_text(toml, encoding="utf-8", newline="\n")
print(f"wrote {p}")
print(f"walkmesh: {len(wv)} verts, {len(faces)} tris, {len(order)} floor(s) -- org=0")
print(f"\nDeploy:  py tools/deploy_field.py {p.as_posix()}")
