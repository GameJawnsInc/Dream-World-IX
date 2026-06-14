"""The FF9 area-title overlay manifest -- WHICH scene overlays carry a field's localized "area title"
card (the big "Ice Cavern" / "Mognet Central" lettering shown on entry).

Engine background: the title is NOT a UI banner and NOT a passive engine fade -- it is a range of scene
OVERLAYS, listed per-field in the TextAsset ``mapLocalizeAreaTitle.txt`` (columns:
``mapName, atlasW, atlasH, startOvrIdx, endOvrIdx, hasUK, ...``). The engine only re-textures that range
from ``atlas_<lang>`` for the 38 fields in ``FieldMap.fieldMapNameWithAreaTitle`` -- it never shows, hides
or fades them; the DONOR field's own ``.eb`` scripts the show+fade (scenario-gated). A fork / BG-borrow
that doesn't carry that script leaves the overlays in their default (active) state, so the title sits there
statically. :mod:`ff9mapkit.content.areatitle` uses these indices to script the lifecycle ourselves.

Offline: reads ``x64/FF9_Data/resources.assets`` via UnityPy (a DIFFERENT source than the kit's usual
``p0data*.bin`` -- the manifest lives in the main Unity build, not the field bundles). Degrades to ``{}``
/ ``None`` if UnityPy or the file is absent, so callers no-op cleanly. Provenance-clean: ships nothing,
reads the user's own install at author time.
"""

from __future__ import annotations

import functools

from . import config, extract

MANIFEST_NAME = "mapLocalizeAreaTitle"      # the TextAsset's m_Name (matched with/without a .txt suffix)


@functools.lru_cache(maxsize=4)
def _manifest(game_key: str | None = None) -> dict:
    """``{donor_fbg: (startOvrIdx, endOvrIdx)}`` parsed from resources.assets; ``{}`` if unavailable."""
    try:
        UnityPy = extract._unitypy()
    except Exception:
        return {}
    game = config.find_game_path(game_key)
    if game is None:
        return {}
    candidates = [game / "x64" / "FF9_Data" / "resources.assets",
                  game / "FF9_Data" / "resources.assets",
                  game / "x86" / "FF9_Data" / "resources.assets"]
    for res in candidates:
        if not res.exists():
            continue
        try:
            env = UnityPy.load(str(res))
        except Exception:
            continue
        for obj in env.objects:
            if obj.type.name != "TextAsset":
                continue
            try:
                data = obj.read()
            except Exception:
                continue
            name = str(getattr(data, "m_Name", None) or getattr(data, "name", ""))
            if name.rsplit(".", 1)[0] != MANIFEST_NAME:    # m_Name is "mapLocalizeAreaTitle.txt"
                continue
            raw = extract._raw_bytes(data)
            txt = raw.decode("utf-8", "replace") if isinstance(raw, (bytes, bytearray)) else str(raw)
            out: dict = {}
            for line in txt.splitlines():
                cols = [c.strip() for c in line.split(",")]
                if len(cols) >= 5 and cols[0]:
                    try:
                        out[cols[0]] = (int(cols[3]), int(cols[4]))
                    except ValueError:
                        continue           # header / malformed row
            return out
    return {}


def title_range(donor_fbg: str, game=None) -> "tuple[int, int] | None":
    """The ``(startOvrIdx, endOvrIdx)`` scene-overlay range carrying ``donor_fbg``'s area title, or
    ``None`` if the field has no area title (the vast majority -- 636 of 674). ``donor_fbg`` is the real
    field's full FBG name, e.g. ``"FBG_N05_ICCV_MAP085_IC_ENT_0"``."""
    key = str(game) if game is not None else None
    return _manifest(key).get(donor_fbg)
