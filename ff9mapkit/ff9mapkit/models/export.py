"""Orchestrate a model export: real GEO -> ``{geoId}.fbx`` (skinned ASCII) + textures on the user's disk.

Fork-fidelity path (``docs/CUSTOM_MODELS.md``). The output filename + layout match the engine's disc
override: ``ModelFactory.CreateModel`` probes ``Models/{typeInt}/{geoId}/{geoId}.fbx`` in the mod folder
BEFORE the bundle, so dropping the exported (or edited) FBX there replaces that model in-game -- no DLL.

Provenance: everything is written to the caller's ``out_dir`` (gitignored), read live from the user's
own install; zero Square-Enix bytes touch the repo.
"""
from __future__ import annotations

from pathlib import Path

from . import extract, fbx_skin


def engine_rel_path(type_int: int, geo_id: int) -> str:
    """The mod-folder-relative path the engine looks for this model at (loose-override target)."""
    return f"StreamingAssets/Assets/Resources/Models/{type_int}/{geo_id}/{geo_id}.fbx"


def export_model(token: str, out_dir, *, game=None, flat: bool = False) -> dict:
    """Export a real model (GEO name or id) -> a skinned FBX-ASCII + PNG textures + manifest.

    ``flat=False`` (default) writes the engine override layout under ``out_dir`` --
    ``Models/{type}/{geoId}/{geoId}.fbx`` + ``{stem}.png`` -- so the folder can be copied straight into a
    mod folder. ``flat=True`` writes ``{geoId}.fbx`` + textures directly in ``out_dir`` (for editing).
    Returns a manifest dict (geo, geo_id, type_int, bones, meshes, verts, textures, fbx path, meta)."""
    model = extract.read_model(token, game=game)
    merge_warnings: list = []
    extract.merge_nested_child_meshes(model, warn=merge_warnings.append)   # fold nested-child meshes the loose-FBX importer would drop
    text, meta = fbx_skin.emit_skinned_fbx(model)

    out = Path(out_dir)
    if flat:
        dest = out
    else:
        dest = out / "Models" / str(model["type_int"]) / str(model["geo_id"])
    dest.mkdir(parents=True, exist_ok=True)
    fbx_path = dest / f'{model["geo_id"]}.fbx'
    fbx_path.write_text(text, encoding="ascii", newline="\n")
    saved = []
    for stem, img in model["textures"].items():
        p = dest / f"{stem}.png"
        img.save(str(p))
        saved.append(f"{stem}.png")

    verts = sum(len(m["verts"]) for m in model["meshes"])
    return {
        "geo": model["geo"], "geo_id": model["geo_id"], "type_int": model["type_int"],
        "bones": meta["bones"], "meshes": meta["meshes"], "materials": meta["materials"],
        "verts": verts, "textures": saved, "euler_max_err": meta["euler_max_err"],
        "merge_warnings": merge_warnings,
        "fbx": str(fbx_path), "engine_path": engine_rel_path(model["type_int"], model["geo_id"]),
    }


def deploy_override(token: str, mod_folder, *, game=None) -> dict:
    """Export the (unedited) model straight into ``mod_folder`` at the engine override path -- the Phase-1
    fidelity test: does the loose FBX render + animate identically to the bundled model in-game."""
    model = extract.read_model(token, game=game)
    merge_warnings: list = []
    extract.merge_nested_child_meshes(model, warn=merge_warnings.append)   # fold nested-child meshes the loose-FBX importer would drop
    text, meta = fbx_skin.emit_skinned_fbx(model)
    dest = Path(mod_folder) / "StreamingAssets" / "Assets" / "Resources" / "Models" \
        / str(model["type_int"]) / str(model["geo_id"])
    dest.mkdir(parents=True, exist_ok=True)
    (dest / f'{model["geo_id"]}.fbx').write_text(text, encoding="ascii", newline="\n")
    for stem, img in model["textures"].items():
        img.save(str(dest / f"{stem}.png"))
    return {"geo": model["geo"], "geo_id": model["geo_id"], "merge_warnings": merge_warnings,
            "path": str(dest / f'{model["geo_id"]}.fbx'), "euler_max_err": meta["euler_max_err"]}
