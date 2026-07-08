"""Texture RESKIN -- the cheapest model edit: one PNG, no Blender, no FBX, no DLL.

Engine facts (direct source, ``ModelFactory.cs:100-116``): for every BUNDLE-loaded model,
``CreateModel`` (``checkTextureOnDisc`` defaults true) probes ``<model dir>/{textureName}.png`` on
disc per material and swaps the texture in when found -- so dropping a loose ``{stem}.png`` (stem =
the texture's own name, e.g. ``8_0``) at the model's override dir reskins it with NO mesh + NO FBX.
Weapons take exactly this path too (``btl_eqp.InitWeapon`` calls CreateModel with the probe on;
their dir is ``BattleMap/BattleModel/6/{id}``). If a loose FBX override IS also deployed, the FBX
importer reads the same-named PNGs from the same dir -- so the target directory is identical either
way (:func:`..export.model_dir_parts` is the single source of truth).

Two engine opt-outs where the probe is forced OFF (documented; not fixable data-side): Zidane's
F3/F4/F5 alt-costume texture-reassign branch, and a field carrying a ``CustomModelField`` per-map
swap for that model.

Names are the contract: an edited file must keep its ``{stem}.png`` name or the probe never finds
it -- :func:`deploy_reskin` validates every file against the model's real stems and fails loud.
"""
from __future__ import annotations

import shutil
from pathlib import Path

from . import export as mexport
from . import extract

_RESKIN_OPTOUT = {"GEO_MAIN_F3_ZDN", "GEO_MAIN_F4_ZDN", "GEO_MAIN_F5_ZDN"}


def _model_textures(token: str, game=None) -> tuple:
    """(model struct, {stem: PIL.Image}) -- fails loud on a texture-less model (nothing to reskin)."""
    model = extract.read_model(token, game=game)
    textures = model.get("textures") or {}
    if not textures:
        raise ValueError(f"{model['geo']} carries no textures -- nothing to reskin")
    return model, textures


def export_textures(token: str, out_dir, *, game=None) -> dict:
    """Write a model's pristine textures as editable ``{stem}.png`` files. Edit them in any image
    editor (any size works -- the engine takes upscales), keep the NAMES, then :func:`deploy_reskin`."""
    model, textures = _model_textures(token, game=game)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    written = []
    for stem, img in textures.items():
        p = out / f"{stem}.png"
        img.save(str(p))
        written.append({"name": f"{stem}.png", "size": list(img.size)})
    return {"geo": model["geo"], "geo_id": model["geo_id"], "dir": str(out), "textures": written,
            "warnings": _optout_warnings(model["geo"])}


def validate_reskin_names(stems, png_paths) -> tuple:
    """Pure: check every PNG's basename against the model's texture stems. Returns
    ``(ok_paths, errors)`` -- an unknown name is an ERROR (the engine probe would never find it)."""
    stems = set(stems)
    ok, errors = [], []
    for p in map(Path, png_paths):
        if p.suffix.lower() != ".png":
            errors.append(f"{p.name}: not a .png (the engine probe reads PNG only)")
        elif p.stem not in stems:
            errors.append(f"{p.name}: no texture named {p.stem!r} on this model "
                          f"(its textures: {', '.join(sorted(stems))})")
        else:
            ok.append(p)
    return ok, errors


def _optout_warnings(geo: str) -> list:
    if geo in _RESKIN_OPTOUT:
        return [f"{geo} is one of Zidane's alt-costume forms -- the engine reassigns its textures "
                "in code and SKIPS the loose-PNG probe for it (ModelFactory.cs:75-91). A PNG-only "
                "reskin will NOT show; deploy a full model override instead (model-export --deploy)."]
    return []


def recolor_image(img, *, hue=None, tint=None):
    """Pure declarative recolor -- the palette-swap primitive. ``hue`` rotates the hue wheel by
    degrees (the classic Goblin -> red-Goblin move: geometry-safe, keeps shading/detail);
    ``tint`` = [r, g, b] channel multipliers (e.g. [1.4, 0.7, 0.7] pushes red). Both compose
    (hue first). Alpha is preserved untouched -- FF9 materials are cutout-alpha, so a recolor must
    never disturb the mask. Returns a new RGBA image; the input is not mutated."""
    from PIL import Image
    out = img.convert("RGBA")
    r, g, b, a = out.split()
    rgb = Image.merge("RGB", (r, g, b))
    if hue:
        h, s, v = rgb.convert("HSV").split()
        shift = int(round(float(hue) / 360.0 * 256.0)) % 256
        if shift:
            h = h.point(lambda x, _s=shift: (x + _s) % 256)
        rgb = Image.merge("HSV", (h, s, v)).convert("RGB")
    if tint:
        mr, mg, mb = (float(t) for t in tint)
        chans = []
        for ch, m in zip(rgb.split(), (mr, mg, mb)):
            chans.append(ch.point(lambda x, _m=m: min(255, max(0, int(round(x * _m))))))
        rgb = Image.merge("RGB", chans)
    return Image.merge("RGBA", (*rgb.split(), a))


def deploy_reskin(token: str, png_paths, mod_folder, *, game=None) -> dict:
    """Copy edited ``{stem}.png`` files into ``mod_folder`` at the model's override dir. Validates
    names against the model's real stems (fail loud -- a mis-named PNG silently never loads) and
    that each file is a readable image; a size differing from the original is fine (noted, the
    engine accepts upscales)."""
    model, textures = _model_textures(token, game=game)
    ok, errors = validate_reskin_names(textures.keys(), png_paths)
    if errors:
        raise ValueError("reskin refused:\n  " + "\n  ".join(errors))
    from PIL import Image
    notes = _optout_warnings(model["geo"])
    dest = Path(mod_folder).joinpath("StreamingAssets", "Assets", "Resources",
                                     *mexport.model_dir_parts(model["type_int"], model["geo_id"]))
    dest.mkdir(parents=True, exist_ok=True)
    deployed = []
    for p in ok:
        try:
            with Image.open(p) as im:
                size = im.size
        except Exception as e:   # noqa: BLE001 -- any unreadable/corrupt file must not deploy
            raise ValueError(f"{p.name}: not a readable image ({e})") from e
        orig = textures[p.stem].size
        if size != orig:
            notes.append(f"{p.name}: {size[0]}x{size[1]} vs the original {orig[0]}x{orig[1]} "
                         "(fine -- the engine takes any size; UVs are relative)")
        shutil.copyfile(p, dest / p.name)
        deployed.append(p.name)
    return {"geo": model["geo"], "geo_id": model["geo_id"], "dir": str(dest),
            "deployed": deployed, "warnings": notes}
