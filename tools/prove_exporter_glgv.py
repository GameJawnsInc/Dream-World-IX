#!/usr/bin/env python3
"""Prove the ff9mapkit EXPORTER in-game.

Fork GLGV as a full CUSTOM SCENE (NOT borrow) whose walkmesh is RE-EXPORTED from the real field's
.bgi: import it (BgiWalkmesh.world_verts -> world coords) then write it back via bgi.build (world
frame, orgPos=0, every floor.org=0). Pair it with GLGV's real camera (camera.bgx) + its composited
art (background.png). If the player walks a floor aligned with the art in-game, the new exporter is
engine-validated -- the kit produced a walkmesh the engine renders exactly where authored.

Run:  py tools/prove_exporter_glgv.py        # writes tools/scroll_out/glgv_exp/
then:  py tools/deploy_field.py tools/scroll_out/glgv_exp/GLGV_EXP.field.toml
"""
import os
import shutil
import sys
from pathlib import Path

KIT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ff9mapkit"))
sys.path.insert(0, KIT)
from ff9mapkit.scene import bgi

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "tools" / "scroll_out" / "glgv_import"
OUT = ROOT / "tools" / "scroll_out" / "glgv_exp"
OUT.mkdir(parents=True, exist_ok=True)

# 1) RE-EXPORT the walkmesh: import (world_verts) -> bgi.build (world frame, org=0) -> walkmesh.obj.
#    The .obj carries the exact world coords; `[walkmesh] frame="world"` makes the kit emit org=0.
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

# 2) reuse GLGV's REAL camera + composited art verbatim
shutil.copyfile(SRC / "camera.bgx", OUT / "camera.bgx")
shutil.copyfile(SRC / "background.png", OUT / "background.png")

# 3) custom-scene field.toml: NO borrow_bg => the kit writes its own .bgx (GLGV camera + the art
#    overlay) + our re-exported .bgi. A Vivi NPC + spawn confirm content lands on the re-exported floor.
spawn = (1430, -205)
toml = f"""# EXPORTER PROOF -- GLGV forked as a CUSTOM SCENE. The walkmesh below is RE-EXPORTED from the
# real field's .bgi via ff9mapkit's world-frame builder (bgi.build, orgPos=0). If the player walks a
# floor aligned with the art, the exporter is engine-validated.
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

[[layers]]
image = "background.png"
z = 4000

[player]
spawn = [{spawn[0]}, {spawn[1]}]

[[npc]]
name = "Vivi"
preset = "vivi"
pos = [{spawn[0]}, {spawn[1] + 250}]
dialogue = "Re-exported walkmesh. If I'm planted on the floor, the exporter works."
"""
p = OUT / "GLGV_EXP.field.toml"
p.write_text(toml, encoding="utf-8", newline="\n")

print(f"wrote {p}")
print(f"walkmesh: {len(wv)} verts, {len(faces)} tris, {len(order)} floor(s) -- re-exported at org=0")
print(f"\nDeploy:  py tools/deploy_field.py {p.as_posix()}")
