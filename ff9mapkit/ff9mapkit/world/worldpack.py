"""Codec for the overworld ``discmr.img`` -- the baked binary that holds the random-encounter TABLE (no DLL).

The overworld's native tables live in one image asset per disc, ``WorldMap/wmap/disc{1,4}/discmr.img`` (p0data
container ``assets/resources/worldmap/wmap/disc{1,4}/discmr.img.bytes``). It is a **two-layer container**:

  1. **Sector TOC** -- the first 2048-byte sector is ``256 x {Int32 start; Int32 length}`` (both in 2048-byte disc
     sectors; ``ff9.cs:3626-3633``). Record **1** locates the data pack.
  2. **Pointer-table pack** (``w_memorySPSData``; ``sectorInfo[1]``) -- ``[UInt32 count][UInt32 off0..offN]`` then
     the payloads; sub-table ``no`` starts at ``pack[ off[no] ]`` (``w_framePackExtractPosition``, ``ff9.cs:4267``).

The two encounter tables (indices baked in the engine, ``ff9.cs:9591+``):

  * **sub-table 3** = ``EncountData[355]`` -- ``{UInt16 scene[4]; Byte pattern; Byte pad}`` (10 B packed). A record
    is chosen by zone-slice x ``topograph = pattern>>2`` x ``fog = pad&1`` (``w_worldGetBattleScenePtr``,
    ``ff9.cs:9079``); ``scene[0..2]`` = the normal battle-scene ids, ``scene[3]`` = the friendly/special variant.
  * **sub-table 4** = ``sworldEncountSpecial[9]`` -- ``{UInt16 area[12]}`` (the 9 Friendly-Monster creatures; a
    non-zero ``area[j]`` is a 1-based index into the 355 table, ``0xFFFF`` = empty).

**Re-tabling only changes record VALUES, never counts**, so edits are a pure IN-PLACE byte rewrite of the two
tables at their absolute file offsets -- no pointer/offset repack, the 2-byte pad after the encount table and every
other pack section stay verbatim, and ``Discmr(x).to_bytes() == x`` for an unedited image. Deploy is a whole-file
override at ``<mod>/StreamingAssets/<container>`` (``AssetManager.LoadBytes`` honors it, ``AssetManager.cs:593``);
RELAUNCH to apply. This is the *table* axis; the *rate* axis is the lighter ``world/encounter.py``.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass, field

SECTOR = 2048
TOC_RECORDS = 256                 # w_fileImageSectorInfo = new sw_ImageSector[256] (ff9.cs:350)
PACK_SECTION = 1                  # w_memorySPSData <- sectorInfo[1] (ff9.cs:8676)
ENCOUNT_IDX = 3                   # kWorldPackEncountTable
SPECIAL_IDX = 4                   # kWorldPackEncountSpecial
ENCOUNT_COUNT = 355              # ReadEncountData loops 355 (WMBinarayReaderExtension.cs:84)
ENCOUNT_SIZE = 10                 # u16 scene[4] + u8 pattern + u8 pad
SPECIAL_COUNT = 9                 # ReadWorldEncountSpecial loops 9
SPECIAL_SIZE = 24                 # u16 area[12]
SPECIAL_EMPTY = 0xFFFF            # an unused area slot
_CONTAINER_RE = "worldmap/wmap/disc{disc}/discmr"


@dataclass
class EncountRecord:
    """One overworld encounter-table row. ``scene`` = 4 battle-scene ids (``scene[3]`` = the friendly variant);
    ``topograph`` = ``pattern>>2`` (the terrain this row answers for), ``fog`` = ``pad&1`` (mist vs clear twin)."""
    scene: list                   # 4 x UInt16
    pattern: int                  # topograph in bits 2..7, low 2 bits = a scene-slot selector
    pad: int                      # bit 0 = fog

    @property
    def topograph(self) -> int:
        return self.pattern >> 2

    @property
    def fog(self) -> int:
        return self.pad & 1


@dataclass
class Discmr:
    """A parsed ``discmr.img``. Edit :attr:`encounters` (355) / :attr:`specials` (9 x 12) in place, then
    :meth:`to_bytes`. ``container`` / ``disc`` are set by :func:`load_discmr` for deploy."""
    _data: bytearray
    pack_off: int
    offs: list                    # pack pointer table (count+1 absolute-in-pack offsets)
    encounters: list              # ENCOUNT_COUNT x EncountRecord
    specials: list                # SPECIAL_COUNT x list[12]
    container: str | None = None
    disc: int | None = None
    enc_abs: int = 0
    special_abs: int = 0

    # -- parse --
    @classmethod
    def from_bytes(cls, data: bytes, *, container: str | None = None, disc: int | None = None) -> "Discmr":
        b = bytearray(data)
        if len(b) < SECTOR:
            raise ValueError(f"discmr.img too small ({len(b)} B) -- not a valid image")
        start, length = struct.unpack_from("<ii", b, PACK_SECTION * 8)
        pack_off, pack_len = start * SECTOR, length * SECTOR
        if pack_off <= 0 or pack_off + 12 > len(b):
            raise ValueError(f"discmr.img sector-TOC record {PACK_SECTION} out of range (start={start} len={length})")
        count = struct.unpack_from("<I", b, pack_off)[0]
        if count > 4096 or pack_off + 4 * (count + 2) > len(b):
            raise ValueError(f"discmr.img pack pointer-table count {count} implausible")
        offs = [struct.unpack_from("<I", b, pack_off + 4 + k * 4)[0] for k in range(count + 1)]
        if count < max(ENCOUNT_IDX, SPECIAL_IDX):
            raise ValueError(f"discmr.img pack has only {count} sub-tables (need >= {SPECIAL_IDX})")
        enc_abs = pack_off + offs[ENCOUNT_IDX]
        special_abs = pack_off + offs[SPECIAL_IDX]
        if enc_abs + ENCOUNT_COUNT * ENCOUNT_SIZE > len(b) or special_abs + SPECIAL_COUNT * SPECIAL_SIZE > len(b):
            raise ValueError("discmr.img encounter/special table runs past end of file")
        encounters = []
        for i in range(ENCOUNT_COUNT):
            base = enc_abs + i * ENCOUNT_SIZE
            scene = list(struct.unpack_from("<4H", b, base))
            encounters.append(EncountRecord(scene=scene, pattern=b[base + 8], pad=b[base + 9]))
        specials = [list(struct.unpack_from("<12H", b, special_abs + i * SPECIAL_SIZE)) for i in range(SPECIAL_COUNT)]
        return cls(_data=b, pack_off=pack_off, offs=offs, encounters=encounters, specials=specials,
                   container=container, disc=disc, enc_abs=enc_abs, special_abs=special_abs)

    # -- serialize (writes the two tables back into a copy of the original bytes; everything else verbatim) --
    def to_bytes(self) -> bytes:
        out = bytearray(self._data)
        for i, r in enumerate(self.encounters):
            base = self.enc_abs + i * ENCOUNT_SIZE
            if len(r.scene) != 4:
                raise ValueError(f"encounter[{i}].scene must have 4 ids (got {len(r.scene)})")
            struct.pack_into("<4H", out, base, *(s & 0xFFFF for s in r.scene))
            out[base + 8] = r.pattern & 0xFF
            out[base + 9] = r.pad & 0xFF
        for i, area in enumerate(self.specials):
            if len(area) != 12:
                raise ValueError(f"special[{i}].area must have 12 slots (got {len(area)})")
            struct.pack_into("<12H", out, self.special_abs + i * SPECIAL_SIZE, *(a & 0xFFFF for a in area))
        return bytes(out)

    # -- edits --
    def set_encounter(self, i: int, *, scene=None, pattern=None, pad=None):
        """Set fields of record ``i`` (0..354). ``scene`` may be a 4-list (all slots) or a ``{slot: id}`` dict."""
        r = self.encounters[i]
        if isinstance(scene, dict):
            for slot, sid in scene.items():
                r.scene[int(slot)] = int(sid) & 0xFFFF
        elif scene is not None:
            if len(scene) != 4:
                raise ValueError(f"scene must be 4 ids or a {{slot: id}} dict (got {scene!r})")
            r.scene = [int(s) & 0xFFFF for s in scene]
        if pattern is not None:
            r.pattern = int(pattern) & 0xFF
        if pad is not None:
            r.pad = int(pad) & 0xFF

    def remap_scene(self, mapping: dict) -> int:
        """Replace battle-scene ids across ALL 4 slots of ALL records (``{old_id: new_id}``). Returns the count of
        slots changed. Use for 'swap formation X for Y everywhere'."""
        m = {int(k) & 0xFFFF: int(v) & 0xFFFF for k, v in mapping.items()}
        n = 0
        for r in self.encounters:
            for j, sid in enumerate(r.scene):
                if sid in m and m[sid] != sid:
                    r.scene[j] = m[sid]
                    n += 1
        return n

    def match(self, *, index=None, topograph=None, fog=None) -> list:
        """Indices of records matching the filter: an exact ``index``, and/or a ``topograph`` (``pattern>>2``) with
        optional ``fog`` (0/1). No filter -> every record."""
        out = []
        for i, r in enumerate(self.encounters):
            if index is not None and i != index:
                continue
            if topograph is not None and r.topograph != topograph:
                continue
            if fog is not None and r.fog != int(bool(fog)):
                continue
            out.append(i)
        return out


# --------------------------------------------------------------------------- p0data load + mod deploy

def load_discmr(disc: int = 1, game=None) -> Discmr:
    """Load + parse ``discmr.img`` for ``disc`` (1 or 4) from the install's p0data. Prefers an already-deployed
    mod-folder override? No -- always the pristine base image (edits should start clean). Raises if not found."""
    from pathlib import Path
    from . import extract as X
    X._unitypy()
    needle = _CONTAINER_RE.format(disc=disc)
    for path in sorted(X._bundles(game), key=lambda p: (0 if "p0data3." in Path(p).name else 1, p)):
        try:
            env = X._load_env(path)
        except Exception:                                # noqa: BLE001 -- odd/non-bundle file, keep scanning
            continue
        for o in env.objects:
            if o.type.name != "TextAsset":
                continue
            c = (getattr(o, "container", None) or "")
            if needle in c.lower():
                s = o.read().m_Script
                data = s.encode("utf-8", "surrogateescape") if isinstance(s, str) else bytes(s)
                return Discmr.from_bytes(data, container=c.lstrip("/").lower(), disc=disc)
    raise ValueError(f"discmr.img for disc {disc} not found in StreamingAssets/p0data*.bin "
                     f"(looked for container {needle!r}) -- is this a full FF9 install?")


def deploy_discmr(discmr: Discmr, *, mod_folder: str, game=None, dry_run: bool = False):
    """Write ``discmr`` as a whole-file mod override at ``<mod>/StreamingAssets/<container>`` (the path
    ``AssetManager`` checks, ``AssetManager.cs:593``). Returns the written ``Path``. RELAUNCH to apply."""
    from pathlib import Path
    from .. import config
    if not discmr.container:
        raise ValueError("discmr has no container path (load it via load_discmr)")
    root = config.find_mod_root(config.find_game_path(game), mod_folder)
    dest = Path(root) / "StreamingAssets" / discmr.container
    if not dry_run:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(discmr.to_bytes())
    return dest


# --------------------------------------------------------------------------- declarative edit config

def apply_config(discmr: Discmr, cfg: dict) -> dict:
    """Apply a ``[[set]]`` / ``[remap]`` edit config to ``discmr`` (in place). Returns a summary
    ``{sets: [...], remapped: N}``. ``[[set]]`` = {index | topograph [+ fog], scene=[4] | scene0..3, pattern, pad};
    ``[remap]`` = {old_scene_id: new_scene_id} applied to every slot."""
    summary = {"sets": [], "remapped": 0}
    for k, item in enumerate(cfg.get("set", []) or []):
        if not isinstance(item, dict):
            raise ValueError(f"[[set]] #{k} must be a table")
        idx = item.get("index")
        topo = item.get("topograph")
        if idx is None and topo is None:
            raise ValueError(f"[[set]] #{k} needs a matcher: `index` or `topograph`")
        targets = discmr.match(index=idx, topograph=topo, fog=item.get("fog"))
        if not targets:
            raise ValueError(f"[[set]] #{k} matched no records (index={idx} topograph={topo} fog={item.get('fog')})")
        scene = item.get("scene")
        if scene is None:                                # per-slot scene0..scene3
            per = {s: item[f"scene{s}"] for s in range(4) if f"scene{s}" in item}
            scene = per or None
        for i in targets:
            discmr.set_encounter(i, scene=scene, pattern=item.get("pattern"), pad=item.get("pad"))
        summary["sets"].append({"match": {"index": idx, "topograph": topo, "fog": item.get("fog")},
                                "count": len(targets)})
    remap = cfg.get("remap") or {}
    if remap:
        summary["remapped"] = discmr.remap_scene(remap)
    return summary
