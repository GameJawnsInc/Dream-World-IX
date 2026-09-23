"""The field **MapConfigData** (MCF) decoder -- ``CommonAsset/MapConfigData/<EVT_name>.bytes``.

The MCF is how a real field gives its 3D models their LIGHT and their BLOB SHADOW. Every one of the
818 shipping fields carries one; a kit-synthesized field carries none (only a native fork ships its
donor's verbatim, via ``[field] mapconfig``). At field load ``HonoluluFieldMain`` reads it into
``map.mcfPtr``; every frame ``fldmcf.ff9fieldMCFService`` then, per actor, picks the actor's
``DMSMapChar`` row (by model id, else the ``0xFFFF`` default row) plus the ``DMSMapLight`` of the
walkmesh floor it stands on (else the type-1 default light), and calls::

    FF9ShadowSetAmpField(uid, (char.shadowI + light.shadowI) << 3)
    FF9ShadowSetScaleField(uid, char.shadowR + light.shadowR, <same>)

With ``mcfPtr == null`` that service returns at its first line, and ``new FF9Shadow()`` stays at
``xScale = zScale = 0`` -- the shadow quad is collapsed to nothing on the actor's first render
(``EventEngine.SetRenderer``). That is why a kit field's actors cast no shadow.
(:mod:`ff9mapkit.content.shadow` restores it with the script ops that call the SAME two functions.)

Layout (``MapConfiguration.DMSParseMapConfFile``, little-endian): a 12-byte header
``attr u16, version u16, bgNo u16, lightCount/lightUse/charCount/charUse/evtCount/evtUse u8``,
then ``lightCount`` x 12-byte lights ``type,no,shadowI,shadowR i8, clr[4] i8, floor[4] i8``, then
``charCount`` x 8-byte chars ``geoNo u16, shadowI,shadowR i8, clr[3] i8, shadowZ i8``.
Pure decode -- no Square-Enix bytes live in this module.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass, field

DEFAULT_GEO = 0xFFFF            # the default DMSMapChar row (ff9fieldMCFGetCharByID(-1) masks -1 to 0xFFFF)
LIGHT_FLOOR, LIGHT_DEFAULT, LIGHT_LADDER = 0, 1, 2      # DMSMapLight.type


@dataclass(frozen=True)
class MapLight:
    type: int
    no: int
    shadow_i: int
    shadow_r: int
    clr: tuple
    floor: tuple


@dataclass(frozen=True)
class MapChar:
    geo: int
    shadow_i: int
    shadow_r: int
    clr: tuple
    shadow_z: int


@dataclass(frozen=True)
class MapConfig:
    attr: int
    version: int
    bg_no: int
    light_use: int
    char_use: int
    lights: tuple = field(default_factory=tuple)
    chars: tuple = field(default_factory=tuple)

    def char(self, model: int):
        """The row ``ff9fieldMCFGetCharByID`` returns for ``model`` -- searched from ``charUse - 1`` DOWN
        to 0, first match wins -- or None."""
        model &= 0xFFFF
        for c in reversed(self.chars[:self.char_use]):
            if c.geo == model:
                return c
        return None

    def default_light(self):
        """The LAST type-1 (default) light among the first ``lightUse`` -- ``ff9fieldMCFGetLightDefault``
        walks them in reverse and keeps overwriting, so the LOWEST index wins. Mirrored exactly."""
        found = None
        for lt in reversed(self.lights[:self.light_use]):
            if lt.type == LIGHT_DEFAULT:
                found = lt
        return found

    def effective_shadow(self, model: int):
        """``(shadowI, shadowR)`` the engine applies to ``model`` on a floor with no floor-specific light:
        the model's row (else the 0xFFFF default row) plus the default light. None when neither char
        row exists (the engine would throw there -- no shipping MCF lacks the default row)."""
        c = self.char(model) or self.char(DEFAULT_GEO)
        if c is None:
            return None
        lt = self.default_light()
        return (c.shadow_i + (lt.shadow_i if lt else 0), c.shadow_r + (lt.shadow_r if lt else 0))


_HEADER = 12
_LIGHT_SIZE = 12
_LIGHT_FLOOR_AT = 8             # the four floor bytes inside a 12-byte light
FLOOR_UNUSED = -1               # an empty floor slot: the engine masks it to 255, which never names a floor


def remap_light_floors(data: bytes, floor_map: dict) -> bytes:
    """``data`` with every per-floor light (type 0) re-keyed through ``floor_map`` (donor floor -> the
    walkmesh's floor), everything else byte-identical. A donor floor ``floor_map`` does not name (it is not
    in the walkmesh any more) becomes :data:`FLOOR_UNUSED`, so its light matches nothing.

    Why: ``ff9fieldMCFGetLightByCharFloor`` matches ``light.floor[i] & 255`` against the BGI floor index the
    actor stands on (``FieldMapActorController.activeFloor``). A reshaped walkmesh that renumbers its floors
    would otherwise light floor 2 with floor 1's colour and shadow."""
    b = bytearray(data)
    count = b[6]                                           # lightCount (the header's 7th byte)
    for k in range(count):
        at = _HEADER + k * _LIGHT_SIZE
        if struct.unpack_from("<b", b, at)[0] != LIGHT_FLOOR:
            continue
        for s in range(4):
            v = struct.unpack_from("<b", b, at + _LIGHT_FLOOR_AT + s)[0]
            if v == FLOOR_UNUSED:
                continue
            struct.pack_into("<b", b, at + _LIGHT_FLOOR_AT + s, int(floor_map.get(v & 0xFF, FLOOR_UNUSED)))
    return bytes(b)


def lit_floors(data: bytes) -> set:
    """The floors that have their OWN light (a type-0 light within ``lightUse`` names them)."""
    mc = parse(data)
    return {f & 0xFF for lt in mc.lights[:mc.light_use] if lt.type == LIGHT_FLOOR
            for f in lt.floor if f != FLOOR_UNUSED}


def parse(data: bytes) -> MapConfig:
    """Decode one MapConfigData blob (see the module docstring for the layout)."""
    b = bytes(data)
    attr, ver, bg, lc, lu, cc, cu, _ec, _eu = struct.unpack_from("<HHHBBBBBB", b, 0)
    off = 12
    lights = []
    for _ in range(lc):
        t, no, si, sr = struct.unpack_from("<4b", b, off)
        lights.append(MapLight(t, no, si, sr, struct.unpack_from("<4b", b, off + 4),
                               struct.unpack_from("<4b", b, off + 8)))
        off += 12
    chars = []
    for _ in range(cc):
        geo, si, sr = struct.unpack_from("<Hbb", b, off)
        chars.append(MapChar(geo, si, sr, struct.unpack_from("<3b", b, off + 4),
                             struct.unpack_from("<b", b, off + 7)[0]))
        off += 8
    return MapConfig(attr, ver, bg, lu, cu, tuple(lights), tuple(chars))
