"""Palette-swap enemy authoring -- ``[[scene.enemy]] skin = {...}`` mints a RECOLORED variant model.

The classic FF9 move (Goblin -> Goblin Mage) as one declarative knob. A body re-skin
(:mod:`.reskin`, ``model =``) points an enemy at a DIFFERENT stock creature; a *skin* keeps the
creature and changes its COLORS -- by minting the enemy's model at a NEW GEO id (>= 6000) with
transformed textures, so the original stays vanilla everywhere else:

  [[scene.enemy]]
  type = 0
  skin = { id = 6200, hue = 150 }                                # hue-rotate the whole palette
  # skin = { id = 6200, tint = [1.4, 0.7, 0.7] }                 # or channel multipliers
  # skin = { id = 6200, textures = { "152_0" = "my_gob.png" } }  # or hand-painted texture(s)
  # optional: from = "GEO_MON_B3_001" (default: this type's own model), name = "GEO_MON_B3_XYZ"

Why it works (all previously proven pieces): the enemy's model is ``Geo@30`` in its
``SB2_MON_PARM`` (an i16 -- the 6000..32767 mint band fits); a ``3DModel <id> <name>`` directive
registers the id at launch; the engine then loads our loose FBX at ``Models/3/<id>/``; and the
UNTOUCHED ``Mot[6]`` anim ids keep playing the source's clips, which bind by bone name onto the
minted mesh (identical skeleton -- the same mint-borrows-animset mechanism the 13th character's
6100 battle model uses). Unlike a cross-model body re-skin there is NO animation retarget quirk:
the skeleton is the source's own. RELAUNCH to register the id (DictionaryPatch loads at startup).
"""
from __future__ import annotations

import struct

from . import scene_data

_GEO_OFF = 30                                    # Geo (i16 model id) inside the 116-byte SB2_MON_PARM
_MINT_MIN, _MINT_MAX = 6000, 32767               # mint band floor .. i16 ceiling (Geo@30 is signed 16-bit)


class SkinError(scene_data.SceneEditError):
    pass


def skin_spec(enemy) -> "dict | None":
    """Validate one ``[[scene.enemy]]``'s ``skin`` table -> a normalized spec, or None when absent.
    Pure/install-free (the offline validate path runs it). Fails loud on every malformed shape --
    a bad skin must never silently ship an un-recolored or unregistered model."""
    if not isinstance(enemy, dict) or enemy.get("skin") is None:
        return None
    raw = enemy["skin"]
    if not isinstance(raw, dict):
        raise SkinError(f"skin must be a table {{ id = ..., hue/tint/textures = ... }}, got {type(raw).__name__}")
    sid = raw.get("id")
    if not isinstance(sid, int) or isinstance(sid, bool) or not _MINT_MIN <= sid <= _MINT_MAX:
        raise SkinError(f"skin.id must be an int in the mint band {_MINT_MIN}..{_MINT_MAX} "
                        f"(Geo@30 is a signed 16-bit field), got {sid!r}")
    if "type" not in enemy:
        raise SkinError(f"a skinned enemy needs `type = N` (which monster block gets the minted model)")
    hue = raw.get("hue")
    if hue is not None and (isinstance(hue, bool) or not isinstance(hue, (int, float))):
        raise SkinError(f"skin.hue must be a number of degrees, got {hue!r}")
    tint = raw.get("tint")
    if tint is not None:
        if (not isinstance(tint, list) or len(tint) != 3
                or any(isinstance(t, bool) or not isinstance(t, (int, float)) or t < 0 for t in tint)):
            raise SkinError(f"skin.tint must be [r, g, b] non-negative multipliers, got {tint!r}")
    textures = raw.get("textures")
    if textures is not None:
        if (not isinstance(textures, dict)
                or any(not isinstance(k, str) or not isinstance(v, str) for k, v in textures.items())):
            raise SkinError(f"skin.textures must be a table of {{ \"<stem>\" = \"<png path>\" }}, got {textures!r}")
    if hue is None and tint is None and not textures:
        raise SkinError(f"skin id={sid} does nothing -- give at least one of hue / tint / textures")
    name = raw.get("name")
    if name is not None and not isinstance(name, str):
        raise SkinError(f"skin.name must be a GEO_<GROUP>_<FORM>_<TOKEN> string, got {name!r}")
    return {"id": sid, "type": int(enemy["type"]), "hue": hue, "tint": tint,
            "textures": dict(textures or {}), "from": raw.get("from"), "name": name}


def _read_geo(raw16: bytes, t: int) -> int:
    patcount, typcount, _ = scene_data.parse_counts(raw16)
    if not 0 <= t < typcount:
        raise SkinError(f"skin: enemy type {t} out of range (this scene has {typcount} type(s))")
    off = scene_data._mon_base(patcount) + 116 * t + _GEO_OFF
    return struct.unpack_from("<h", raw16, off)[0]


def _write_geo(raw16: bytes, t: int, geo_id: int) -> bytes:
    patcount, typcount, _ = scene_data.parse_counts(raw16)
    b = bytearray(raw16)
    struct.pack_into("<h", b, scene_data._mon_base(patcount) + 116 * t + _GEO_OFF, geo_id)
    return bytes(b)


def apply_skins(raw16: bytes, scene_cfg: dict, layout, *, game=None, base_dir=None):
    """Mint every skinned enemy's recolored model into ``layout`` and point its ``Geo@30`` at the
    mint. Returns ``(raw16', dict_lines, written, warnings)``. Runs AFTER ``apply_scene_edits`` (so
    a co-authored body re-skin's transplanted Geo is what a from-less skin recolors). Install-gated
    (reads the source model live); a skin-free scene never touches the install."""
    specs = []
    for e in scene_cfg.get("enemy") or []:
        s = skin_spec(e)
        if s is not None:
            specs.append(s)
    if not specs:
        return raw16, [], [], []

    from pathlib import Path

    from ..models import extract as mextract
    from ..models import fbx_skin as mfbx
    from ..models import mint as mmint
    from ..models import reskin as mreskin
    from .._modeldb import MODELS

    dict_lines, written, warnings = [], [], []
    seen_ids = set()
    for s in specs:
        if s["id"] in seen_ids:
            raise SkinError(f"skin id {s['id']} used twice -- each skinned enemy needs its own mint id")
        seen_ids.add(s["id"])
        # the source model: an explicit `from`, else the type's CURRENT Geo (post body-re-skin)
        if s["from"] is not None:
            src_geo, _sid, _tint = mextract.resolve_geo(str(s["from"]))
        else:
            cur = _read_geo(raw16, s["type"])
            src_geo = MODELS.get(cur)
            if not src_geo:
                raise SkinError(f"skin: enemy type {s['type']}'s model id {cur} is not in the GEO table -- "
                                f"give an explicit from = \"GEO_MON_B3_...\"")
        name = s["name"] or mmint.derive_mint_name(src_geo, s["id"])
        mmint.validate_mint_name(name)

        model = mextract.read_model(src_geo, game=game)
        mextract.merge_nested_child_meshes(model, warn=warnings.append)
        text, _meta = mfbx.emit_skinned_fbx(model)
        dest = layout.model_dir(model["type_int"], s["id"])
        dest.mkdir(parents=True, exist_ok=True)
        fbx_path = dest / f"{s['id']}.fbx"
        fbx_path.write_text(text, encoding="ascii", newline="\n")
        written.append(fbx_path)

        overrides = {}
        for stem, p in s["textures"].items():
            if stem not in model["textures"]:
                raise SkinError(f"skin id={s['id']}: no texture named {stem!r} on {src_geo} "
                                f"(its textures: {', '.join(sorted(model['textures']))})")
            path = Path(p)
            if not path.is_absolute() and base_dir is not None:
                path = Path(base_dir) / path
            if not path.is_file():
                raise SkinError(f"skin id={s['id']}: texture file not found: {path}")
            overrides[stem] = path
        from PIL import Image
        for stem, img in model["textures"].items():
            if stem in overrides:
                out_img = Image.open(overrides[stem]).convert("RGBA")
            elif s["hue"] is not None or s["tint"] is not None:
                out_img = mreskin.recolor_image(img, hue=s["hue"], tint=s["tint"])
            else:
                out_img = img
            png = dest / f"{stem}.png"
            out_img.save(str(png))
            written.append(png)

        raw16 = _write_geo(raw16, s["type"], s["id"])
        dict_lines.append(f"3DModel {s['id']} {name}")
        ops = ", ".join(x for x in ((f"hue {s['hue']:g}°" if s["hue"] is not None else ""),
                                    (f"tint {s['tint']}" if s["tint"] is not None else ""),
                                    (f"{len(overrides)} texture override(s)" if overrides else "")) if x)
        warnings.append(f"type {s['type']}: palette-swapped {src_geo} -> mint {s['id']} ({name}; {ops}). "
                        f"Its animations are the source's own (same skeleton, no retarget quirk). "
                        f"RELAUNCH to register the minted id (DictionaryPatch loads at startup)")
    return raw16, dict_lines, written, warnings
