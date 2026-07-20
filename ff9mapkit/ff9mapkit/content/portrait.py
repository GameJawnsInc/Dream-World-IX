"""``[[playable]] portrait`` -- a CUSTOM menu portrait (avatar) for a 13th character, DLL-free.

The menu/battle-result portrait is an NGUI ``UISprite`` whose ``spriteName`` = the character's
``BattleParameters.csv`` ``AvatarSprite`` value (``FF9UIDataTool.AvatarSpriteName`` ->
``btl_mot.BattleParameterList[serial].AvatarSprite``). The base faces (``face00``..``face12``, 132x190) live in
the **"Face Atlas"** NGUI atlas.

★ THE OVERRIDE HOOK (verified vs ``UIAtlas.cs`` + proven by Moguri on the install): every ``UIAtlas`` registers a
load-time ``OverrideAtlas`` hook that probes each mod folder for a loose ``FF9_Data/EmbeddedAsset/UI/Atlas/<Atlas
Name>.png`` (+ a ``.png.tpsheet`` sidecar). With **``:append=true``** the tpsheet's sprite rects are MERGED into
the atlas by name and each appended sprite carries its OWN loose texture (``UISpriteData.texture = atlasTexture``,
``UIAtlas.cs:136``) -- so a brand-new ``face_cuNN`` sprite is added NON-destructively (the stock faces + any
Moguri reskin are untouched). No bundle repack, no DLL; read once at ``GameLoopManager.Start`` -> RELAUNCH to apply.

So a custom portrait = (a) ship ``Face Atlas.png`` (the packed portrait image(s)) + ``Face Atlas.png.tpsheet`` (an
append sheet naming each portrait's rect), and (b) point the character's ``AvatarSprite`` at that sprite name
(:func:`sprite_name`). The tpsheet grammar mirrors Moguri's proven ``General Atlas.png.tpsheet``:
``:format=40000`` / ``:size=WxH`` / ``:append=true`` / ``<name>;<x>;<y>;<w>;<h>;0;0;0;0;0;0;0;0;0;0`` (x,y =
top-left origin).
"""
from __future__ import annotations

from pathlib import Path

FACE_W, FACE_H = 132, 190          # the stock face-sprite size (uniform for all base faces); the recommended portrait size
ATLAS_PNG = "Face Atlas.png"       # the loose override file (matches GraphicResources.AtlasList["Face Atlas"])
ATLAS_TPSHEET = "Face Atlas.png.tpsheet"


class PortraitError(ValueError):
    pass


def sprite_name(playable_id: int) -> str:
    """The unique atlas sprite name for a custom character's portrait (won't collide with the stock ``faceNN``)."""
    return f"face_cu{int(playable_id)}"


def load_portrait(path, *, base_dir=None):
    """Load a portrait PNG -> an RGBA :class:`PIL.Image`. ``base_dir`` roots a relative path. Warns (via the
    returned list) if it isn't the recommended 132x190. Raises :class:`PortraitError` if unreadable."""
    from PIL import Image
    p = Path(path)
    if not p.is_absolute() and base_dir is not None:
        p = Path(base_dir) / p
    if not p.is_file():
        raise PortraitError(f"[[playable]] portrait image not found: {p}")
    try:
        img = Image.open(p).convert("RGBA")
    except Exception as ex:
        raise PortraitError(f"[[playable]] portrait {p}: could not read the image ({ex})")
    warnings = []
    if (img.width, img.height) != (FACE_W, FACE_H):
        warnings.append(f"[[playable]] portrait {p.name} is {img.width}x{img.height}, not the stock face size "
                        f"{FACE_W}x{FACE_H} -- it will be scaled to the avatar slot (aspect may distort)")
    return img, warnings


def build_face_atlas(portraits):
    """``[{name, image (RGBA PIL)}]`` -> ``(sheet_image, tpsheet_text)``. Packs the portraits into one horizontal
    strip (each at its own x, top-left y=0) and emits the ``:append=true`` tpsheet. Order-stable; empty -> (None, "")."""
    from PIL import Image
    items = [(p["name"], p["image"]) for p in portraits if p.get("image") is not None]
    if not items:
        return None, ""
    width = sum(im.width for _, im in items)
    height = max(im.height for _, im in items)
    sheet = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    rows, x = [], 0
    for name, im in items:
        sheet.paste(im, (x, 0))
        rows.append(f"{name};{x};0;{im.width};{im.height};0;0;0;0;0;0;0;0;0;0")
        x += im.width
    tpsheet = "\n".join([":format=40000", f":size={width}x{height}", ":append=true", *rows]) + "\n"
    return sheet, tpsheet


def write_face_atlas(layout, portraits) -> list:
    """Write the loose ``Face Atlas.png`` + ``Face Atlas.png.tpsheet`` (append) into ``layout``'s
    ``FF9_Data/EmbeddedAsset/UI/Atlas/``. No portraits -> nothing written. Returns warnings."""
    sheet, tpsheet = build_face_atlas(portraits)
    if sheet is None:
        return []
    d = layout.face_atlas_dir
    d.mkdir(parents=True, exist_ok=True)
    sheet.save(str(d / ATLAS_PNG))
    (d / ATLAS_TPSHEET).write_text(tpsheet, encoding="utf-8", newline="\n")
    return ["[[playable]] portrait -> a loose Face Atlas override (append) is read at LAUNCH -> RELAUNCH to apply "
            "(a menu reload won't); it adds the sprite(s) non-destructively (stock faces + a Moguri reskin are untouched)"]
