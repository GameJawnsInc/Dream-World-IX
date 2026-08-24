"""Mint a NEW GEO model id -- an ADDITIVE custom model that doesn't displace a real one.

DLL-FREE. The engine already ships everything needed (verified in the pinned build 6b8bb2d5):

  * ``3DModel <id> <GEO_NAME>`` (DictionaryPatch directive, ``DataPatchers.cs:574``) registers
    ``FF9BattleDB.GEO[id] = name`` at load -- a runtime addition to the id<->name two-way dict that the
    whole model pipeline keys on. Read once at launch (like a ``FieldScene`` line), so a NEW id needs one
    relaunch to register.
  * ``ModelFactory.CreateModel`` resolves ``SetModel(id)`` -> ``GEO.GetValue(id)`` -> name ->
    ``Models/{typeInt}/{id}/{id}.fbx`` and probes the mod folder FIRST (``ModelImporter.CreateCustomModelFromFbx``
    -- the loose-FBX importer, no DLL). ``GetModelType(name)`` derives the typeInt from the name's GROUP.
  * Animations resolve by the ANIM NAME's tokens (``AnimationFactory.AddAnimWithAnimatioName`` ->
    ``Animations/GEO_{grp}_{form}_{tok}/{anim}`` -> ``GetRenameAnimationPath`` -> the by-id folder), NOT the
    model's own id -- so a minted model REUSES a real model's animset simply by playing its ``ANH_`` names,
    and our exporter preserves the ``bone{NNN}`` numbering so the clips bind. (Custom anims are also possible
    via the ``3DModelAnimation`` directive + ``.anim`` files, but reuse needs neither.)

So minting = (a) export the (source or edited) model to the new id's loose-FBX path, (b) emit one
``3DModel`` line, (c) place it with ``[[npc]]/[[prop]] model = <id>`` (a raw id passes through
``resolve_npc_model``). Real GEO ids run 0..5511, so the mint band is >= 6000 (clear of every real id;
``SetModel`` takes a 2-byte id, max 65535).
"""
from __future__ import annotations

import re
from pathlib import Path

from .. import fsutil
from . import extract, fbx_skin

MINT_BAND_START = 6000                       # first id clear of every real GEO id (real max = 5511)
_GROUP_TYPE = extract._TYPE_INT              # {'acc':1,'main':2,'mon':3,'npc':4,'sub':5,'wep':6}


def type_int_of_name(name: str) -> int:
    """GEO name -> engine typeInt from its GROUP (GEO_<GROUP>_<form>_<token>), matching GetModelType."""
    parts = name.split("_")
    grp = parts[1].lower() if len(parts) > 1 else ""
    tint = _GROUP_TYPE.get(grp)
    if tint is None:
        raise ValueError(f"mint name {name!r} has unknown group {grp!r} (want one of {sorted(_GROUP_TYPE)}) "
                         f"-- the group sets the model TYPE + the Models/<type>/ path")
    return tint


def derive_mint_name(source_geo: str, new_id: int) -> str:
    """A NOVEL GEO name for a mint: keep the source's GROUP+FORM (so type + anim-token linkage carry) but a
    fresh TOKEN derived from the id -- so it never collides with a real name in the value-reverse map (which
    would hijack the real model's GetGEOID path). The token is the id's band OFFSET (bijective with the id),
    so two mints never share a name (a shared name would make one mint's SetModel resolve the other's FBX).
    e.g. GEO_NPC_F1_BBA + 6000 -> GEO_NPC_F1_M000, + 6042 -> GEO_NPC_F1_M042."""
    parts = source_geo.split("_")
    grp, form = parts[1], parts[2]
    tok = f"M{new_id - MINT_BAND_START:03d}"   # M000, M001, ... -- unique per id, outside FF9's token space
    return f"GEO_{grp}_{form}_{tok}"


def validate_mint_name(name: str):
    if not re.fullmatch(r"GEO_[A-Z]+_[A-Za-z0-9]+_[A-Za-z0-9]+", name):
        raise ValueError(f"mint name {name!r} must look like GEO_<GROUP>_<FORM>_<TOKEN> (e.g. GEO_NPC_F0_M00)")
    if name in extract._NAME_TO_ID:
        raise ValueError(f"mint name {name!r} is a REAL FF9 model name -- reusing it would hijack that model's "
                         f"id<->name reverse lookup. Use a novel token (see derive_mint_name).")
    type_int_of_name(name)                    # group must be valid


def mint_manifest(source_token: str, new_id: int, new_name: "str | None" = None, *, game=None) -> dict:
    """Resolve a mint spec WITHOUT writing anything: the new id/name/type + the DictionaryPatch directive +
    the animset the placed model should borrow (the source's, by name)."""
    if new_id < MINT_BAND_START:
        raise ValueError(f"mint id {new_id} is below the mint band {MINT_BAND_START} (real GEO ids go 0..5511; "
                         f"a lower id would collide with / overwrite a real model)")
    src_geo, src_id, _ = extract.resolve_geo(source_token)
    name = new_name or derive_mint_name(src_geo, new_id)
    validate_mint_name(name)
    # Borrow the source's animset: its {stand,walk,run,left,right} anim IDS resolve (via AnimationDB ->
    # the ANIM NAME's tokens) to the SOURCE model's anim folder, independent of the mint's own id -- so
    # placing the mint with these plays the source's gestures on the minted mesh (bone numbers preserved).
    from .. import catalog
    anims = catalog.npc_anims(src_geo) or None
    return {"id": new_id, "name": name, "type_int": type_int_of_name(name),
            "source": src_geo, "source_id": src_id, "anims_from": src_geo, "anims": anims,
            "directive": f"3DModel {new_id} {name}"}


def export_mint(source_token: str, new_id: int, dest_dir, new_name=None, *, game=None) -> dict:
    """Export the source model's geometry -> the mint's loose-FBX at ``dest_dir/{new_id}.fbx`` + textures.

    ``dest_dir`` is the target model folder (the caller places it at Models/{type}/{new_id}/). The FBX body
    is geometry + skeleton (bone numbers preserved) -- identical to a same-model override; only the on-disc
    id (the folder + filename) changes. Returns the manifest (+ the written paths)."""
    man = mint_manifest(source_token, new_id, new_name, game=game)
    model = extract.read_model(source_token, game=game)
    merge_warnings: list = []
    extract.merge_nested_child_meshes(model, warn=merge_warnings.append)   # fold nested-child meshes the loose-FBX importer would drop
    text, meta = fbx_skin.emit_skinned_fbx(model)
    man["merge_warnings"] = merge_warnings
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)
    (dest / f"{new_id}.fbx").write_text(text, encoding="ascii", newline="\n")
    saved = []
    for stem, img in model["textures"].items():
        img.save(str(dest / f"{stem}.png"))
        saved.append(f"{stem}.png")
    man.update(fbx=str(dest / f"{new_id}.fbx"), textures=saved, euler_max_err=meta["euler_max_err"])
    return man


def resolve_mint(block: dict, *, game=None) -> dict:
    """A ``[[mint]]`` block dict -> a manifest (NO I/O): id, name, type_int, the ``3DModel`` directive, and
    the animset a placement should borrow. Two forms:
      * ``from = "<GEO>"``  -- re-export a real model to the new id (a duplicate / the proof case); name +
        animset auto-derive from the source.
      * ``fbx = "<path>"``  -- ship an author's custom/edited FBX; needs an explicit novel ``name`` (its
        GROUP sets the type + path) and, to animate, ``anims_from = "<GEO>"`` (a skeleton-compatible real
        model whose gestures the placement borrows)."""
    if "id" not in block:
        raise ValueError("[[mint]] needs an `id` (>= 6000, clear of every real GEO id)")
    new_id = int(block["id"])
    src, fbx, name = block.get("from"), block.get("fbx"), block.get("name")
    anims_from = block.get("anims_from") or src
    if src and fbx:
        raise ValueError(f"[[mint]] id={new_id} has both `from` and `fbx` -- pick one (re-export a real "
                         f"model OR ship a custom FBX)")
    if src:
        man = mint_manifest(src, new_id, name, game=game)
    elif fbx:
        if not name:
            raise ValueError(f"[[mint]] id={new_id} with `fbx` needs `name = \"GEO_<GROUP>_<FORM>_<TOKEN>\"` "
                             f"-- the GROUP sets the model TYPE and the Models/<type>/ path")
        if new_id < MINT_BAND_START:
            raise ValueError(f"mint id {new_id} is below the mint band {MINT_BAND_START} (real GEO ids 0..5511)")
        validate_mint_name(name)
        anims = None
        if anims_from:
            from .. import catalog
            anims = catalog.npc_anims(anims_from) or None
        man = {"id": new_id, "name": name, "type_int": type_int_of_name(name), "source": None,
               "fbx": fbx, "anims_from": anims_from, "anims": anims,
               "directive": f"3DModel {new_id} {name}"}
    else:
        raise ValueError(f"[[mint]] id={new_id} needs `from = \"<GEO>\"` (re-export a real model) or "
                         f"`fbx = \"<path>\"` (ship a custom model)")
    return man


def stage_mint(block: dict, dest_dir, *, base_dir=None, game=None) -> dict:
    """Realize one ``[[mint]]`` into ``dest_dir`` (the target Models/<type>/<id>/ folder): re-export the
    ``from`` model OR copy the ``fbx`` file (+ its adjacent PNG textures) to ``<id>.fbx``. ``base_dir``
    roots a relative ``fbx`` path. Returns the manifest (+ the ``3DModel`` directive to register)."""
    from pathlib import Path as _P
    man = resolve_mint(block, game=game)
    dest = _P(dest_dir)
    if man["source"] is not None:                       # from = re-export a real model
        export_mint(man["source"], man["id"], dest, new_name=man["name"], game=game)
    else:                                               # fbx = ship a custom model
        src_fbx = _P(man["fbx"])
        if not src_fbx.is_absolute() and base_dir is not None:
            src_fbx = _P(base_dir) / src_fbx
        if not src_fbx.is_file():
            raise FileNotFoundError(f"[[mint]] id={man['id']} fbx not found: {src_fbx}")
        dest.mkdir(parents=True, exist_ok=True)
        # byte-verbatim: an author's FBX may be Kaydara BINARY, not ASCII -- any text decode corrupts it
        (dest / f"{man['id']}.fbx").write_bytes(src_fbx.read_bytes())
        for png in src_fbx.parent.glob("*.png"):        # ship the model's textures alongside
            (dest / png.name).write_bytes(png.read_bytes())
    return man


def deploy_mint(source_token: str, new_id: int, mod_folder, new_name=None, *, game=None) -> dict:
    """Export a mint straight into ``mod_folder`` at the engine override path Models/{type}/{new_id}/ AND
    append its ``3DModel`` line to the mod's DictionaryPatch.txt (idempotent). RELAUNCH to register the id."""
    man = mint_manifest(source_token, new_id, new_name, game=game)
    from . import export
    dest = Path(mod_folder).joinpath(*export._RES, *export.model_dir_parts(man["type_int"], new_id))
    dp = Path(mod_folder) / "DictionaryPatch.txt"
    # FOLDER lock around the WHOLE live mutation (the Models/ tree export AND the registration), OUTSIDE
    # the sidecar (lock order: folder THEN sidecar): a wholesale campaign/journey install cannot hold a
    # sidecar inside a tree it deletes, so without this the export + line could land between its snapshot
    # and rmtree and be silently destroyed. A FileLockTimeout propagates (the CLI prints and aborts).
    with fsutil.locked_mod_folder(Path(mod_folder)):
        export_mint(source_token, new_id, dest, new_name=man["name"], game=game)
        dp.parent.mkdir(parents=True, exist_ok=True)      # the lock sidecar needs the folder to exist
        # LOCKED read->merge->write (fsutil.locked_sidecar -- the same DictionaryPatch.txt.lock every deploy
        # script holds): the idempotent append still rewrites the whole file from what it READ, so an unlocked
        # window drops whichever lines a concurrent deploy/revert merged in between. A FileLockTimeout
        # propagates to the caller (the CLI prints and aborts).
        with fsutil.locked_sidecar(dp):
            lines = dp.read_text(encoding="utf-8").splitlines() if dp.exists() else []
            if man["directive"] not in lines:
                lines.append(man["directive"])
                fsutil.atomic_write_text(dp, "\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    man["dictionary_patch"] = str(dp)
    return man
