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

_RES = ("StreamingAssets", "Assets", "Resources")   # AssetManager searches models under Resources/


def model_dir_parts(type_int: int, geo_id: int) -> tuple:
    """Directory parts UNDER ``Resources/`` where the engine probes this model's ``.fbx`` + textures.
    Weapons (``GEO_WEP_*`` = type 6) live under ``BattleMap/BattleModel/``; every other model under
    ``Models/`` -- matching ``ModelFactory.GetRenameModelPath`` (ModelFactory.cs:26-34, the ``GEO_WEP``
    special-case). This is the single source of truth for the loose-override on-disk layout."""
    top = ("BattleMap", "BattleModel") if type_int == 6 else ("Models",)
    return (*top, str(type_int), str(geo_id))


def deploy_target(model: dict) -> tuple[int, int]:
    """(type_int, geo_id) of the loose-override folder the ENGINE probes for this model -- the PREFAB
    identity. ``SearchAssetOnDisc`` runs on ``GetRenameModelPath``'s output, i.e. AFTER the alias
    chain: an aliased battle form's override must land at its donor prefab's folder (GEO_MAIN_B0_000
    -> ``Models/2/98/``); its own-id path is never probed. NOTE that donor folder is shared -- every
    form loading that prefab (Zidane's field AND battle forms) picks the override up. Falls back to
    the requested identity for structs without prefab keys (foreign glTF re-rigs, mints)."""
    return (int(model.get("prefab_tint") or model["type_int"]),
            int(model.get("prefab_id") or model["geo_id"]))


def engine_rel_path(type_int: int, geo_id: int) -> str:
    """The mod-folder-relative path the engine looks for this model at (loose-override target)."""
    return "/".join((*_RES, *model_dir_parts(type_int, geo_id), f"{geo_id}.fbx"))


def _shared_prefab_warnings(model: dict) -> list:
    """Deploy-time caveats for a model whose override folder is SHARED with other forms."""
    out = []
    pgeo = model.get("prefab_geo")
    if pgeo and pgeo != model["geo"]:
        others = f"every form sharing it ({pgeo} and its aliases)"
        out.append(f"{model['geo']}'s geometry ships in donor prefab {pgeo} (id {model.get('prefab_id')}) "
                   f"-- the override lands in THAT folder and affects {others}.")
    if model["geo"] in extract._ALT_TEXTURE_FORMS:
        out.append(f"{model['geo']} is an alt-costume form: its textures were exported with the "
                   f"alt-costume art under the SHARED prefab stems, so deploying them reskins the base "
                   f"outfit too (in-game the engine assigns alt art in code, bundle loads only).")
    return out


def export_model(token: str, out_dir, *, game=None, flat: bool = False) -> dict:
    """Export a real model (GEO name or id) -> a skinned FBX-ASCII + PNG textures + manifest.

    ``flat=False`` (default) writes the engine override layout under ``out_dir`` --
    ``Models/{type}/{id}/{id}.fbx`` + ``{stem}.png`` at the PREFAB identity (the folder the engine
    probes; differs from the requested id for alias models) -- so the folder can be copied straight
    into a mod folder; per-mode overlay meshes are stripped like :func:`deploy_override`. ``flat=True``
    writes everything (overlay included) directly in ``out_dir`` (for editing/inspection).
    Returns a manifest dict (geo, geo_id, type_int, bones, meshes, verts, textures, fbx path, meta)."""
    model = extract.read_model(token, game=game)
    merge_warnings: list = []
    if not flat:
        # a loose override can't be mode-hidden by name -- strip only the overlay THIS form's engine
        # by-name hide would drop (its own opposite-mode overlay is real always-visible geometry)
        extract.strip_overlay_meshes(model, warn=merge_warnings.append,
                                     prefixes=extract.overlay_hide_prefixes(token))
        merge_warnings.extend(_shared_prefab_warnings(model))
    extract.merge_nested_child_meshes(model, warn=merge_warnings.append)   # fold nested-child meshes the loose-FBX importer would drop
    text, meta = fbx_skin.emit_skinned_fbx(model)

    ttint, tid = deploy_target(model)
    out = Path(out_dir)
    dest = out if flat else out.joinpath(*model_dir_parts(ttint, tid))
    dest.mkdir(parents=True, exist_ok=True)
    fbx_path = dest / f"{tid}.fbx"
    fbx_path.write_text(text, encoding="ascii", newline="\n")
    saved = []
    for stem, img in model["textures"].items():
        p = dest / f"{stem}.png"
        img.save(str(p))
        saved.append(f"{stem}.png")

    verts = sum(len(m["verts"]) for m in model["meshes"])
    return {
        "geo": model["geo"], "geo_id": model["geo_id"], "type_int": model["type_int"],
        "prefab_geo": model.get("prefab_geo"), "prefab_id": tid, "prefab_tint": ttint,
        "bones": meta["bones"], "meshes": meta["meshes"], "materials": meta["materials"],
        "verts": verts, "textures": saved, "euler_max_err": meta["euler_max_err"],
        "merge_warnings": merge_warnings,
        "fbx": str(fbx_path), "engine_path": engine_rel_path(ttint, tid),
    }


def deploy_override(token: str, mod_folder, *, game=None) -> dict:
    """Export the (unedited) model straight into ``mod_folder`` at the engine override path -- the Phase-1
    fidelity test: does the loose FBX render + animate identically to the bundled model in-game.
    The path is the PREFAB identity (what ``SearchAssetOnDisc`` probes post-alias); per-mode overlay
    meshes are stripped (the engine's name-hide can't fire on a flattened loose FBX -- see
    :func:`~ff9mapkit.models.extract.strip_overlay_meshes`)."""
    model = extract.read_model(token, game=game)
    merge_warnings: list = []
    extract.strip_overlay_meshes(model, warn=merge_warnings.append,
                                 prefixes=extract.overlay_hide_prefixes(token))
    merge_warnings.extend(_shared_prefab_warnings(model))
    extract.merge_nested_child_meshes(model, warn=merge_warnings.append)   # fold nested-child meshes the loose-FBX importer would drop
    text, meta = fbx_skin.emit_skinned_fbx(model)
    ttint, tid = deploy_target(model)
    dest = Path(mod_folder).joinpath(*_RES, *model_dir_parts(ttint, tid))
    dest.mkdir(parents=True, exist_ok=True)
    (dest / f"{tid}.fbx").write_text(text, encoding="ascii", newline="\n")
    for stem, img in model["textures"].items():
        img.save(str(dest / f"{stem}.png"))
    return {"geo": model["geo"], "geo_id": model["geo_id"], "merge_warnings": merge_warnings,
            "path": str(dest / f"{tid}.fbx"), "euler_max_err": meta["euler_max_err"]}
