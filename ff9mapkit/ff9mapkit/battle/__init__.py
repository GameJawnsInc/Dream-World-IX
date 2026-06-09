"""Custom FF9 battle-background (BBG) authoring — the battle analogue of the field pillar.

A battle background is a real textured 3D Unity model whose child meshes are named Group_0/2/4/8.
Memoria's ModelImporter loads a loose ``.fbx`` from the mod folder INSTEAD of the bundle, so a custom
battle map ships as an ASCII FBX (+ ``image#.png`` textures) at ``ModLayout.battlemap_dir(bbg)`` — no
engine rebuild. Proven in-game 2026-06-09 (texture reskin, a synthetic quad, and a faithful BBG_B013
geometry round-trip).

Loop (mirrors fields' import -> build -> deploy):
    ff9mapkit battle-import BBG_B013 --out my_map   # fork a real map -> battle.toml + FBX + textures
    # edit my_map/BBG_B013.fbx in Blender (keep meshes named Group_0/2/4/8) / repaint the PNGs
    ff9mapkit battle-build my_map/battle.toml --out dist
    py tools/deploy_battle.py my_map/battle.toml    # reversible install into the per-worktree mod folder

Modules: ``fbx`` (pure ASCII-FBX emitter + geometry model), ``extract`` (fork a real BBG via UnityPy),
``build`` (BattleProject + build_battle_mod). Provenance: extraction reads the user's install at
runtime; nothing extracted is committed.
"""
from __future__ import annotations

from . import fbx  # noqa: F401  (pure, no I/O — safe to import always)
