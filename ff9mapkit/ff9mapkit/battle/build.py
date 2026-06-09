"""Compile a battle.toml into a Memoria mod (custom battle map). Offline + deterministic (stdlib only).

Mirrors build.FieldProject / build.build_mod. A battle map ships as a loose FBX (+ image#.png textures)
at ModLayout.battlemap_dir(bbg); registration is optional and has three modes:
  * default  -- bbg = an existing real slot -> the FBX OVERRIDES that map (no patch line, no relaunch).
  * repoint  -- repoint_scene = <id> -> a BattlePatch.txt 'BattleBackground' line points that scene's bg
                at `bbg` (relaunch).
  * mint     -- scene_id + scene_name -> a DictionaryPatch 'BattleScene <id> <NAME> <BBG>' line. This is
                EXPERIMENTAL (tier c): a brand-new scene also needs .raw16/.raw17 assets + a camera the
                kit does not yet author, so a bare new id will not load. build_battlemap warns.
"""
from __future__ import annotations

import re
import shutil
import tomllib
from dataclasses import dataclass
from pathlib import Path

from ..config import ModLayout
from . import fbx as _fbx

_BBG_RE = re.compile(r"^BBG_[A-Z]\d+$")


class BattleBuildError(RuntimeError):
    pass


@dataclass
class BattleProject:
    raw: dict
    base_dir: Path

    @classmethod
    def load(cls, toml_path) -> "BattleProject":
        p = Path(toml_path)
        with p.open("rb") as fh:
            raw = tomllib.load(fh)
        return cls(raw, p.parent)

    @property
    def bm(self) -> dict:
        return self.raw.get("battlemap", {})

    @property
    def bbg(self) -> str:
        return self.bm["bbg"]

    @property
    def fbx_rel(self) -> str:
        return self.bm.get("fbx", f"{self.bbg}.fbx")

    def path(self, rel: str) -> Path:
        return (self.base_dir / rel).resolve()


def validate_battle(project: BattleProject) -> list[str]:
    """Return human-readable problems (empty => OK)."""
    problems: list[str] = []
    bm = project.bm
    if not bm:
        return ["[battlemap] section is required"]
    bbg = bm.get("bbg")
    if not bbg:
        problems.append("[battlemap] missing 'bbg' (the slot this map ships as, e.g. BBG_B013)")
    elif not _BBG_RE.match(bbg):
        problems.append(f"[battlemap] bbg {bbg!r} must look like BBG_B013 (BBG_<letter><digits>)")
    if not project.path(project.fbx_rel).is_file():
        problems.append(f"[battlemap] fbx not found: {project.fbx_rel}")
    if "scene_id" in bm and "repoint_scene" in bm:
        problems.append("[battlemap] set only ONE of scene_id (mint) or repoint_scene")
    if "scene_id" in bm and not bm.get("scene_name"):
        problems.append("[battlemap] scene_id (mint) also needs scene_name")
    return problems


@dataclass
class BattleResult:
    bbg: str
    dict_line: str | None
    battle_patch_lines: list  # list[str]
    warnings: list            # list[str]


def build_battlemap(project: BattleProject, layout: ModLayout) -> BattleResult:
    problems = validate_battle(project)
    if problems:
        raise BattleBuildError("battle.toml problems:\n  " + "\n  ".join(problems))
    bbg = project.bbg
    dst = layout.battlemap_dir(bbg)
    dst.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(project.path(project.fbx_rel), dst / f"{bbg}.fbx")
    # ship every image*.png sitting next to the battle.toml (the textures the FBX references)
    for png in sorted(project.base_dir.glob("*.png")):
        shutil.copyfile(png, dst / png.name)

    bm = project.bm
    dict_line = None
    bp: list[str] = []
    warnings: list[str] = []
    if bm.get("scene_id") is not None and bm.get("scene_name"):
        dict_line = f"BattleScene {int(bm['scene_id'])} {bm['scene_name']} {bbg}"
        warnings.append("scene_id MINT is experimental (tier c): a new battle scene also needs its own "
                        ".raw16/.raw17 assets + a camera, which the kit does not yet author -- a bare new "
                        "id will not load. Prefer overriding an existing slot or repoint_scene.")
    if bm.get("repoint_scene") is not None:
        bp.append(f"Battle: {int(bm['repoint_scene'])}")
        bp.append(f"BattleBackground {bbg}")
    return BattleResult(bbg=bbg, dict_line=dict_line, battle_patch_lines=bp, warnings=warnings)


def build_battle_mod(projects, out_root, *, mod_name="FF9CustomMap", author="", description="") -> dict:
    """Build battle map(s) into a mod at ``out_root``; write/append the registration files."""
    layout = ModLayout(Path(out_root).resolve())
    layout.root.mkdir(parents=True, exist_ok=True)
    results = [build_battlemap(p, layout) for p in projects]

    dlines = [r.dict_line for r in results if r.dict_line]
    if dlines:
        # append to any existing DictionaryPatch (so a co-built field mod isn't clobbered)
        prior = (layout.dictionary_patch.read_text(encoding="utf-8").splitlines()
                 if layout.dictionary_patch.exists() else [])
        layout.dictionary_patch.write_text(
            "\n".join([ln for ln in prior if ln.strip()] + dlines) + "\n",
            encoding="utf-8", newline="\n")

    bplines = [ln for r in results for ln in r.battle_patch_lines]
    if bplines:
        prior = (layout.battle_patch.read_text(encoding="utf-8").splitlines()
                 if layout.battle_patch.exists() else [])
        layout.battle_patch.write_text(
            "\n".join([ln for ln in prior if ln.strip()] + bplines) + "\n",
            encoding="utf-8", newline="\n")

    if not layout.mod_description.exists():
        layout.mod_description.write_text(
            "<Mod>\n"
            f"    <Name>{mod_name}</Name>\n"
            f"    <Author>{author}</Author>\n"
            f"    <InstallationPath>{mod_name}</InstallationPath>\n"
            "    <Category></Category>\n"
            f"    <Description>{description}</Description>\n"
            "</Mod>\n",
            encoding="utf-8", newline="\n")

    return {"root": str(layout.root), "maps": [r.bbg for r in results],
            "dictionary": dlines, "battle_patch": bplines,
            "warnings": [w for r in results for w in r.warnings]}
