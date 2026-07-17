"""Inventory + revert of a mod folder's loose MODEL state -- make "what's deployed?" visible.

The loose-override system is write-only by design (drop a file, the engine probes it first), which
makes a mod folder's model state invisible until something looks: a forgotten reskin, a stale mint,
an animation override shadowing a fresh edit. :func:`scan_mod` walks the three override trees the
engine probes -- ``Models/{type}/{id}/`` + ``BattleMap/BattleModel/{type}/{id}/`` (loose FBX
overrides / mints / PNG-only reskins) and ``Animations/{geoId}/*.anim`` (clip overrides) -- plus the
mod's ``DictionaryPatch.txt`` ``3DModel`` mint registrations, and classifies every entry.
:func:`revert_entry` deletes one entry's files (and strips a mint's ``3DModel`` line), path-guarded
to the mod folder. Pure filesystem; no install needed.

Entry kinds:
  * ``override`` -- a loose FBX at a REAL model's id (replaces that model everywhere)
  * ``reskin``   -- PNG(s) with no FBX (texture-only; the engine's per-material disc probe)
  * ``mint``     -- a model dir at a non-real id (>= 6000 band; pairs with a ``3DModel`` line)
  * ``anims``    -- loose ``.anim`` clip override(s) for one model
  * ``mint-directive`` -- a ``3DModel`` line whose model folder is MISSING (dangling registration)
"""
from __future__ import annotations

import shutil
from pathlib import Path

from .. import fsutil

_RES = ("StreamingAssets", "Assets", "Resources")


def _res_root(mod_folder) -> Path:
    return Path(mod_folder).joinpath(*_RES)


def _model_name(geo_id: int):
    from .. import catalog
    m = catalog.model(int(geo_id))
    return m.name if m else None


def _dir_entry(id_dir: Path, gid: int, *, weapon_tree: bool) -> dict:
    files = sorted(p.name for p in id_dir.iterdir() if p.is_file())
    nbytes = sum(p.stat().st_size for p in id_dir.iterdir() if p.is_file())
    has_fbx = f"{gid}.fbx" in files
    name = _model_name(gid)
    if name is None:
        kind = "mint"
    elif has_fbx:
        kind = "override"
    else:
        kind = "reskin" if any(f.lower().endswith(".png") for f in files) else "override"
    return {"kind": kind, "geo_id": gid, "name": name, "dir": str(id_dir), "files": files,
            "nbytes": nbytes, "weapon_tree": weapon_tree, "registered": False}


def parse_mint_directives(mod_folder) -> dict:
    """``{mint_id: name}`` from the mod's DictionaryPatch.txt ``3DModel`` lines (empty if none)."""
    dp = Path(mod_folder) / "DictionaryPatch.txt"
    out = {}
    if not dp.is_file():
        return out
    for line in dp.read_text(encoding="utf-8", errors="replace").splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[0] == "3DModel" and parts[1].isdigit():
            out[int(parts[1])] = parts[2]
    return out


def scan_mod(mod_folder) -> list:
    """Every deployed model-side entry in ``mod_folder``, sorted overrides/reskins -> mints -> anims
    -> dangling directives. Pure filesystem walk (no install); an empty/missing tree returns []."""
    root = _res_root(mod_folder)
    entries: list = []
    trees = [(root / "Models", False), (root / "BattleMap" / "BattleModel", True)]
    for base, weapon_tree in trees:
        if not base.is_dir():
            continue
        for type_dir in sorted(base.iterdir()):
            if not (type_dir.is_dir() and type_dir.name.isdigit()):
                continue
            for id_dir in sorted(type_dir.iterdir()):
                if id_dir.is_dir() and id_dir.name.isdigit() and any(id_dir.iterdir()):
                    entries.append(_dir_entry(id_dir, int(id_dir.name), weapon_tree=weapon_tree))

    anim_root = root / "Animations"
    if anim_root.is_dir():
        for id_dir in sorted(anim_root.iterdir()):
            if not (id_dir.is_dir() and id_dir.name.isdigit()):
                continue
            clips = sorted(p.name for p in id_dir.glob("*.anim"))
            if clips:
                gid = int(id_dir.name)
                entries.append({"kind": "anims", "geo_id": gid, "name": _model_name(gid),
                                "dir": str(id_dir), "files": clips,
                                "nbytes": sum(p.stat().st_size for p in id_dir.glob("*.anim")),
                                "weapon_tree": False, "registered": False})

    directives = parse_mint_directives(mod_folder)
    present = {e["geo_id"] for e in entries if e["kind"] in ("mint", "override", "reskin")}
    for e in entries:
        if e["geo_id"] in directives:
            e["registered"] = True
            if e["name"] is None:
                e["name"] = directives[e["geo_id"]]
    for mid, name in sorted(directives.items()):
        if mid not in present:
            entries.append({"kind": "mint-directive", "geo_id": mid, "name": name,
                            "dir": str(Path(mod_folder) / "DictionaryPatch.txt"), "files": [],
                            "nbytes": 0, "weapon_tree": False, "registered": True})
    order = {"override": 0, "reskin": 1, "mint": 2, "anims": 3, "mint-directive": 4}
    entries.sort(key=lambda e: (order.get(e["kind"], 9), e["geo_id"]))
    return entries


def _strip_mint_directive(mod_folder, geo_id: int) -> bool:
    """Remove ``3DModel <geo_id> ...`` lines from the mod's DictionaryPatch.txt. True if any went."""
    dp = Path(mod_folder) / "DictionaryPatch.txt"
    if not dp.is_file():
        return False
    lines = dp.read_text(encoding="utf-8", errors="replace").splitlines()
    gone = ["3DModel", str(int(geo_id))]
    keep = [ln for ln in lines if ln.split()[:2] != gone]
    if len(keep) == len(lines):
        return False
    fsutil.atomic_write_text(dp, "\n".join(keep) + ("\n" if keep else ""), encoding="utf-8", newline="\n")
    return True


def revert_entry(mod_folder, entry: dict) -> dict:
    """Delete one scanned entry's files; a mint (or a dangling directive) also loses its ``3DModel``
    line. The target path must sit INSIDE the mod folder (a scan entry always does; this guards a
    hand-built one). Returns {removed, directive_removed}. A registered id needs a game relaunch to
    actually unregister -- the caller should say so."""
    mod = Path(mod_folder).resolve()
    removed = []
    if entry["kind"] != "mint-directive":
        target = Path(entry["dir"]).resolve()
        if mod not in target.parents:
            raise ValueError(f"refusing to delete {target} -- not inside the mod folder {mod}")
        if target.is_dir():
            shutil.rmtree(target)
            removed.append(str(target))
    directive_removed = False
    if entry["kind"] in ("mint", "mint-directive"):
        directive_removed = _strip_mint_directive(mod_folder, entry["geo_id"])
    return {"removed": removed, "directive_removed": directive_removed}


def describe(entry: dict) -> str:
    """One human line for a scanned entry (the GUI row / CLI listing)."""
    name = entry["name"] or "?"
    n = len(entry["files"])
    kb = entry["nbytes"] / 1024.0
    what = {"override": "model override", "reskin": "texture reskin", "mint": "minted model",
            "anims": "animation override", "mint-directive": "DANGLING 3DModel line (no folder)"}
    body = f"{what.get(entry['kind'], entry['kind'])} — {name} (id {entry['geo_id']})"
    if n:
        body += f", {n} file(s), {kb:,.0f} KB"
    if entry["kind"] == "mint" and not entry["registered"]:
        body += "  ⚠ no 3DModel line — the id won't register"
    return body
