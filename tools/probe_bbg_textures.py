#!/usr/bin/env python3
"""STEP-1 PROBE: pull a battle background's Texture2D assets out of p0data2.bin (offline, UnityPy).

We need the exact Texture2D.m_Name of each texture a BBG model uses, because Memoria's battle
texture-override (ModelFactory.CreateModel, checkTextureOnDisc=true) searches the mod folder for
``BattleMap/BattleModel/battleMap_all/<BBG>/<material.mainTexture.name>.png``. The filename stem
must equal the runtime ``mat.mainTexture.name`` == the bundle Texture2D's ``m_Name``.

Usage:  py tools/probe_bbg_textures.py BBG_B013 [outdir]
Dumps originals as <m_Name>.png and prints a manifest. Read-only on the game install.
"""
import sys, glob
from pathlib import Path

KIT = str(Path(__file__).resolve().parent.parent / "ff9mapkit")
sys.path.insert(0, KIT)
from ff9mapkit.config import find_game_path  # noqa: E402
import UnityPy  # noqa: E402

bbg = (sys.argv[1] if len(sys.argv) > 1 else "BBG_B013").lower()
outdir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(__file__).resolve().parent / "scroll_out" / "bbg_probe" / bbg
outdir.mkdir(parents=True, exist_ok=True)

game = find_game_path()
sa = game / "StreamingAssets"
needle = f"battlemap_all/{bbg}/"
binpath = sa / "p0data2.bin"
print(f"loading {binpath} ...")
env = UnityPy.load(str(binpath))

seen = {}
for obj in env.objects:
    if obj.type.name != "Texture2D":
        continue
    cont = (getattr(obj, "container", None) or "").lower()
    if needle not in cont:
        continue
    data = obj.read()
    name = data.m_Name
    if name in seen:
        continue
    img = data.image
    img.save(outdir / f"{name}.png")
    seen[name] = (cont, img.size, img.mode)

for name, (cont, size, mode) in sorted(seen.items()):
    print(f"  {name:24s} {size[0]}x{size[1]} {mode}   <- {cont}")
print(f"\n{len(seen)} textures -> {outdir}")
