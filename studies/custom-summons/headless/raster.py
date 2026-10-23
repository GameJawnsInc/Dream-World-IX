r"""RASTER -- draw the headless host's primitives the way Memoria's managed renderer draws them.

    py -I raster.py run --ef 227 --frames 82,300 [--scale 2]      # PNGs + a visibility summary (SCRATCH)
    py -I raster.py run --ef 211 --container <edited> --frames 235-284 --cell x704_y256
    py -I raster.py calibrate --ef 227 --log <s48 capture log>     # the RX gates vs an in-game probe log

WHY THIS EXISTS
---------------
``sfx_host.py`` runs the native plugin and reports what it EMITTED: primitives are data, and "this prim
samples VRAM cell X" is not "a pixel from cell X reached the screen". Between the two sits Memoria's
open-source managed renderer, and it is not a PSX GPU:

* ``SFXRender.Add`` batches every primitive into one ``SFXMesh`` per *mesh key* (texture page + palette
  + blend + filter bits, ``SFXKey``), and ``PushCommandBuffer`` re-orders the batches by blend family
  (``SFX.subOrder``/``addOrder``, per effect from ``SFX.playParam``) -- not by the ordering table.
* Overlap is settled by a DEPTH BUFFER keyed on each prim's OT depth (``GzDepth = -otz``), with the
  opaque shaders writing depth and the add/subtract ones only testing it.
* Textures come from a 50-entry cache of 256x256 decodes (``PSXTextureMgr``), refreshed only when a
  VRAM write lands in the texture's OWN page (``ClearKey``), every decode is bilinear-filtered unless
  the prim asks for point sampling, and a texel is transparent only when its halfword is 0x0000.
* A 15bpp page below x = 384 is never read from VRAM: it is the BLUR texture (the previous frame's
  screen). Once a cast has rendered into the ``DR_AREA`` target, every other 15bpp page samples that
  512x256 render target (VRAM x 384..895, y 256..511) instead of VRAM.
* The three blend shaders (``SFX_OPA/ADD/SUB_G[T]``) ship only a D3D9 program: vertex colour is
  ``rgb * _Color * alpha`` clamped to [0, 1], ``abr`` 0/1/3 all render as ADD at alpha 63/127/31
  (``AbrAlphaData``), ``abr`` 2 as reverse-subtract, and an opaque texel below ``_Threshold`` alpha
  is discarded.

This module ports that path line for line (file:line references inline) and drives it from the same
plugin run, so "visible" stops being a guess. Per frame it writes a PNG of the 320x220 PSX screen and
counts, per mesh and per VRAM cell, the fragments that CHANGED the framebuffer.

NOT modelled (each named again where it matters): the 3D battle scene and its depth buffer (the
headless screen starts black and empty), the battle-ground capture (``BACKGROUND`` textures render
transparent), screenshots (only Slow/Silent Voice read them), the ``.seq`` layer's prevented/recoloured
meshes, widescreen, and repeated renders of one SFX frame at the game's display rate.

PROVENANCE: as ``sfx_host.py`` -- everything derived from a stock container (PNGs, summaries) is written
under SCRATCH only.
"""
from __future__ import annotations

import argparse
import ctypes as C
import json
import struct
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
import sfx_host as H                                   # noqa: E402

RASTER_DIR = H.OUT_DIR / "raster"

# ============================================================== Memoria constants
#: FieldMap.PsxScreenWidthNative / PsxScreenHeightNative -- SFX.ResetViewPort's ortho is 320 x 220.
SCREEN_W, SCREEN_H = 320, 220

# SFXKey.cs
HAS_TEXTURE = 0x8000
ABR_ADD = 0x800000
ABR_SUB = 0x1000000
FILTER_POINT = 0x2000000
FILTER_BILINEAR = 0x4000000
FILTER_MASK = 0x6000000
LINE_POLYGON = 0x8000000
FULL_BLUR_TXTURE = 0x20000000
TEX_KEY_MASK = 0x7FFFFF

#: SFXMesh.AbrAlphaData -- the vertex alpha a semi-transparent prim's mesh gets, by abr.
ABR_ALPHA = (63, 127, 127, 31)
#: SFXMesh.Init ColorData -- ``_Color`` by SFX.colIntensity.
COLOR_DATA = (1.0, 1.5, 2.0)
#: SFXMesh limits (INDICES_MAX / VERTICES_MAX per mesh; POS/TEX/COL_MAX across a frame) and the pool.
INDICES_MAX, VERTICES_MAX = 21000, 14000
POS_MAX, TEX_MAX, COL_MAX = 22000, 19300, 10000
MESH_MAX = 64
SST_MAX_TEXTURE = 50
GEN_X, GEN_Y, GEN_W, GEN_H = 384, 256, 512, 256        # PSXTextureMgr.GEN_TEXTURE_*

#: SFX.playParam, the bits SFX.Play reads (sub order 0-1, colour strength 2-3, threshold 29, add order 28).
#: Transcribed from Memoria SFX.cs (SFX static ctor); every id not listed is 0.
PLAY_PARAM = {
    0: 5, 2: 5, 4: 4, 6: 4, 7: 5, 11: 3, 14: 3, 26: 3, 42: 3, 56: 3, 62: 4, 70: 5, 71: 5, 72: 5, 77: 4,
    78: 3, 79: 3, 86: 1 << 29, 125: 3, 127: 3, 134: 5, 140: 3, 150: 8, 151: 4, 152: 4, 159: 5, 179: 2,
    188: 1, 212: 5, 213: 5, 214: 5, 218: 4, 219: 4, 220: 4, 227: 1, 228: 2, 231: 4, 381: 9, 406: 1,
    420: 5, 424: 1, 446: 2, 490: (1 << 28) | 2,
}
#: SpecialEffect ids SFXRender/SFXMesh special-case. Only Ark and Stop are ported; a run that plays one
#: of the others says so in its summary.
EF_SLOW, EF_STOP, EF_LEVIATHAN, EF_PHOENIX, EF_DETECT, EF_DEVOUR, EF_ARK = 126, 149, 179, 211, 250, 274, 381
EF_SILENT_VOICE, EF_NECRON_DEATH = 395, 435
UNPORTED_SPECIALS = {EF_SLOW: "Slow clock sprite + screenshot twist", EF_DETECT: "Detect's eye UV hack",
                     EF_DEVOUR: "Devour's target screenshot", EF_SILENT_VOICE: "Silent Voice screenshot",
                     EF_NECRON_DEATH: "Necron's custom textures (PSXTextureMgr.SpEff435)"}

KIND_NONE, KIND_IMAGE, KIND_BLUR, KIND_BACKGROUND, KIND_GENERATED, KIND_SCREENSHOT = (
    "NONE", "IMAGE", "BLUR", "BACKGROUND", "GENERATED", "SCREENSHOT")


def play_settings(effnum: int) -> dict:
    """SFX.Play (SFX.cs ~1946): the render-order and colour settings one effect runs under."""
    p = PLAY_PARAM.get(effnum, 0)
    sub = p & 3
    col = (p >> 2) & 3
    return {"sub_order": 2 if sub == 0 else sub - 1,            # SFX.defaultSubOrder = 2
            "col_intensity": 2 if col == 0 else col - 1,        # SFX.defaultColIntensity = 2
            "col_threshold": (p >> 29) & 1, "add_order": (p >> 28) & 1}


# ============================================================== SFXKey (SFXKey.cs, ported as written)
def tpage_key_bits(tpage: int) -> int:
    """``((tpage & 0x1F) | (tpage >> 2 & 0x60)) << 16`` -- page x/y in bits 16-20, bpp in 21-22."""
    return ((tpage & 0x1F) | ((tpage >> 2) & 0x60)) << 16


def blend_mode(key: int) -> int:
    return (key >> 23) & 3


def texture_mode(key: int) -> int:
    return (key >> 21) & 3


def is_texture(key: int) -> bool:
    return bool(key & HAS_TEXTURE)


def is_line(key: int) -> bool:
    return bool(key & LINE_POLYGON)


def is_blur_texture(texture_key: int) -> bool:
    return ((texture_key >> 16) & 0xF) < 6


class KeyState:
    """SFXKey's statics: the DR_TPAGE page/abr, and the abr of the prim that set up the last mesh."""

    def __init__(self) -> None:
        self.cur_page = 0
        self.cur_abr = 0
        self.tmp_abr = 0

    def set_tpage(self, tpage: int) -> None:
        self.cur_page = tpage_key_bits(tpage)
        self.cur_abr = (tpage >> 5) & 3

    def current_abr(self, code: int) -> int:
        self.tmp_abr = self.cur_abr
        if code & 2:
            return ABR_SUB if self.cur_abr == 2 else ABR_ADD
        return 0

    def current_abr_tex(self, code: int, clut: int) -> int:
        self.tmp_abr = self.cur_abr
        # SFXKey.GetCurrentABRTex: ``currentTexPage >> 5 == 2`` is never true (the page bits sit at
        # 16+), so the clut is always folded into the key -- ported as written.
        num = HAS_TEXTURE if (self.cur_page >> 5) == 2 else (clut | HAS_TEXTURE)
        if code & 2:
            num |= ABR_SUB if self.cur_abr == 2 else ABR_ADD
        return num | self.cur_page

    def abr_tex(self, code: int, clut: int, tpage: int) -> int:
        num = tpage_key_bits(tpage)
        abr = (tpage >> 5) & 3
        self.tmp_abr = abr
        num3 = HAS_TEXTURE if (num >> 5) == 2 else (clut | HAS_TEXTURE)     # same never-true test
        if code & 2:
            num3 |= ABR_SUB if abr == 2 else ABR_ADD
        return num3 | num


# ============================================================== VRAM + the texture cache (PSXTextureMgr)
class RasterFault(Exception):
    """Something the managed C# would throw on (an index past an array, the mesh pool running dry)."""


def _rgba_of(px: np.ndarray) -> np.ndarray:
    """PSXTexture.ConvertABGR16toABGR32: 5-bit channels << 3, alpha 0 only for the halfword 0x0000."""
    out = np.empty(px.shape + (4,), np.uint8)
    out[..., 0] = (px & 0x1F) << 3
    out[..., 1] = (px & 0x3E0) >> 2
    out[..., 2] = (px & 0x7C00) >> 7
    out[..., 3] = np.where(px != 0, 255, 0)
    return out


class TextureCache:
    """PSXTextureMgr.list: SST_MAX_TEXTURE keyed 256x256 decodes, generated on first use at render time.

    ``vram`` is a (512, 1024) uint16 view. A key is dropped only by ``clear_key`` -- a write whose origin
    lies in the texture's OWN 64x256 page (PSXTextureMgr.ClearKey) -- or by a reset at SFX.Play."""

    def __init__(self, vram: np.ndarray) -> None:
        self.vram = vram
        self.flat = vram.reshape(-1)
        self.entries: Dict[int, Tuple[int, int, np.ndarray]] = {}     # key -> (tx, ty, rgba float [256,256,4])
        self.generated = 0
        self.full = 0

    def clear_key(self, x: int, y: int) -> None:
        tx, ty = x >> 6, y >> 8
        for k in [k for k, (etx, ety, _) in self.entries.items() if etx == tx and ety == ty]:
            del self.entries[k]

    def get(self, key: int) -> Optional[np.ndarray]:
        """PSXTextureMgr.GetTexture(UInt32 key)."""
        hit = self.entries.get(key)
        if hit is not None:
            return hit[2]
        if len(self.entries) >= SST_MAX_TEXTURE:
            self.full += 1                         # Debug.Assert(false); return null -> mesh not drawn
            return None
        clut_x, clut_y = key & 0x3F, (key >> 6) & 0x1FF
        tx, ty, tp = (key >> 16) & 0xF, (key >> 20) & 1, (key >> 21) & 3
        rgba = self.decode(tp, ty, tx, clut_y, clut_x).astype(np.float32) / 255.0
        self.entries[key] = (tx, ty, rgba)
        self.generated += 1
        return rgba

    def decode(self, tp: int, ty: int, tx: int, clut_y: int, clut_x: int) -> np.ndarray:
        """PSXTexture.CreateBufferColor32 -- flat ``(TY+y)*1024 + TX + x`` indexing, as the C# does."""
        TY, TX = ty << 8, tx << 6
        rows = (TY + np.arange(256))[:, None] * 1024 + TX
        per = {0: 4, 1: 2}.get(tp, 1)
        cols = np.arange(256 // per)[None, :]
        idx = rows + cols
        if idx.max() >= self.flat.size:
            raise RasterFault("IndexOutOfRange decoding page tx=%d ty=%d tp=%d" % (tx, ty, tp))
        hw = self.flat[idx].astype(np.uint32)
        if tp in (0, 1):
            base = (clut_x << 4) + (clut_y << 10)
            if tp == 0:
                nib = np.stack([hw & 0xF, (hw >> 4) & 0xF, (hw >> 8) & 0xF, hw >> 12], axis=-1).reshape(256, 256)
            else:
                nib = np.stack([hw & 0xFF, hw >> 8], axis=-1).reshape(256, 256)
            pidx = base + nib
            if pidx.max() >= self.flat.size:
                raise RasterFault("IndexOutOfRange reading clut (%d,%d)" % (clut_x * 16, clut_y))
            return _rgba_of(self.flat[pidx])
        if tp == 2:
            return _rgba_of(hw.astype(np.uint16))
        out = np.empty((256, 256, 4), np.uint8)                # the C# default: r = lo byte, g = hi
        out[..., 0] = hw & 0xFF
        out[..., 1] = (hw >> 8) & 0xFF
        out[..., 2] = 0
        out[..., 3] = 255
        return out


# ============================================================== primitives -> meshes (SFXRender.Add / SFXMesh)
def _s16(v: int) -> int:
    v &= 0xFFFF
    return v - 0x10000 if v & 0x8000 else v


def _xy(w: int) -> Tuple[int, int]:
    return _s16(w), _s16(w >> 16)


def _rgb(w: int) -> Tuple[int, int, int]:
    return w & 0xFF, (w >> 8) & 0xFF, (w >> 16) & 0xFF


def _uv(w: int) -> Tuple[int, int]:
    return w & 0xFF, (w >> 8) & 0xFF


QUAD_A = ((0, 1, 2), (2, 1, 3))      # F4 / FT4 / BFT4 / GT4 / BGT4
QUAD_B = ((0, 1, 2), (1, 3, 2))      # G4 / Sprite / Tile


class Mesh:
    """One SFXMesh for one frame: its key, shader, alpha, and the vertices/indices its prims appended."""
    __slots__ = ("key", "code", "alpha", "shader", "pos", "col", "uv", "tris", "lines", "prims", "pool_slot",
                 "first_prim")

    def __init__(self, key: int, code: int, tmp_abr: int, effnum: int, pool_slot: int, first_prim: int) -> None:
        self.key = key
        self.code = code
        textured = is_texture(key)
        self.shader = 0 if textured else 3                      # SFXMesh.Setup
        if code & 2:
            self.alpha = ABR_ALPHA[tmp_abr]
            self.shader += blend_mode(key)
            if effnum == EF_STOP and key == 0xD78000:
                self.shader = 2
        else:
            self.alpha = 128
        self.pos: List[Tuple[float, float, float]] = []
        self.col: List[Tuple[int, int, int, int]] = []
        self.uv: List[Tuple[float, float]] = []
        self.tris: List[Tuple[int, int, int]] = []
        self.lines: List[Tuple[int, int]] = []
        self.prims = 0
        self.pool_slot = pool_slot
        self.first_prim = first_prim

    def shade_alpha(self, code: int) -> int:
        """SFXMesh.GetShadeAlpha: raw-texture prims keep the mesh alpha, modulated ones double it."""
        if code & 1:
            return self.alpha
        return min(255, self.alpha << 1)

    @property
    def blend(self) -> int:
        return blend_mode(self.key)


class Command:
    """One command-buffer entry: a mesh, a VRAM move, a screenshot, or a render-texture bracket."""
    __slots__ = ("kind", "mesh", "args")

    def __init__(self, kind: str, mesh: Optional[Mesh] = None, args: tuple = ()) -> None:
        self.kind, self.mesh, self.args = kind, mesh, args


class FrameBuilder:
    """SFXRender.Update + Add + GetMesh + PushCommandBuffer for one frame's prim stream."""

    def __init__(self, effnum: int, settings: dict, keys: KeyState) -> None:
        self.effnum = effnum
        self.settings = settings
        self.keys = keys

    def build(self, prims: Sequence[Tuple[int, bytes, int]], frame_index: int = 0) -> Tuple[List[Command], List[str]]:
        """``prims`` = [(code, body, otz)] in SFX_GetPrim order -> (command buffer, faults)."""
        self.cmds: List[Command] = []
        self.faults: List[str] = []
        self.pool = list(range(MESH_MAX))
        self.lists: Dict[str, List[Mesh]] = {n: [] for n in (
            "opa", "add", "sub", "tex_opa", "tex_add_ps", "tex_add_bl", "tex_sub", "line_opa", "line_add", "line_sub")}
        self.dr_x, self.dr_y = 0, 0                 # SFXMeshBase.drOffsetX/Y (widescreen offset 0)
        self.gpos = self.gtex = self.gcol = 0
        sub_order = self.settings["sub_order"]
        if self.effnum == EF_ARK:                   # SFX.UpdatePlugin / Runtime.Load: Ark swaps mid-cast
            if frame_index >= 1193:
                sub_order = 0
            elif frame_index >= 1004:
                sub_order = 2
        self.sub_order = sub_order
        try:
            for i, (code, body, otz) in enumerate(prims):
                self.z = float(otz)                 # GzDepth = -otz; depth tests compare otz directly
                self.index = i
                self._add(code, body)
            self._push()
        except RasterFault as e:                    # the C# throws out of SFXRender.Update: no final push
            self.faults.append("frame %d prim %d: %s" % (frame_index, self.index, e))
        return self.cmds, self.faults

    # ---- SFXRender.Add
    def _add(self, code: int, body: bytes) -> None:
        n = len(body) // 4
        w = struct.unpack_from("<%dI" % n, body)
        k = self.keys
        base = code & 0xFC
        if base == 32:                                                  # POLY_F3
            self._tri(self._mesh(k.current_abr(code), code), w, col=(0,), xy=(1, 2, 3))
        elif base == 36:                                                # POLY_FT3
            self._tri(self._mesh(k.abr_tex(code, w[2] >> 16, w[4] >> 16), code), w, col=(0,), xy=(1, 3, 5),
                      uv=(2, 4, 6), shade=True)
        elif base == 40:                                                # POLY_F4
            self._quad(self._mesh(k.current_abr(code), code), w, col=(0,), xy=(1, 2, 3, 4), order=QUAD_A)
        elif base == 44:                                                # POLY_FT4
            self._quad(self._mesh(k.abr_tex(code, w[2] >> 16, w[4] >> 16), code), w, col=(0,), xy=(1, 3, 5, 7),
                       uv=(2, 4, 6, 8), shade=True, order=QUAD_A)
        elif base == 48:                                                # POLY_G3
            self._tri(self._mesh(k.current_abr(code), code), w, col=(0, 2, 4), xy=(1, 3, 5))
        elif base == 52:                                                # POLY_GT3
            self._tri(self._mesh(k.abr_tex(code, w[2] >> 16, w[5] >> 16), code), w, col=(0, 3, 6), xy=(1, 4, 7),
                      uv=(2, 5, 8), shade=True)
        elif base == 56:                                                # POLY_G4
            self._quad(self._mesh(k.current_abr(code), code), w, col=(0, 2, 4, 6), xy=(1, 3, 5, 7), order=QUAD_B)
        elif base == 60:                                                # POLY_GT4
            self._quad(self._mesh(k.abr_tex(code, w[2] >> 16, w[5] >> 16), code), w, col=(0, 3, 6, 9),
                       xy=(1, 4, 7, 10), uv=(2, 5, 8, 11), shade=True, order=QUAD_A)
        elif base == 64:                                                # LINE_F2
            self._line(self._mesh(k.current_abr(code) | LINE_POLYGON, code), w, col=(0,), xy=(1, 2))
        elif base == 68:                                                # POLY_FT4 via PolyBFT4 (blur)
            key = k.abr_tex(code, w[2] >> 16, w[4] >> 16) | FILTER_BILINEAR | FULL_BLUR_TXTURE
            self._quad(self._mesh(key, code), w, col=(0,), xy=(1, 3, 5, 7), uv=(2, 4, 6, 8), order=QUAD_A,
                       blur_uv=True)
        elif base == 72:                                                # POLY_GT4 via PolyBGT4 (blur)
            key = k.abr_tex(code, w[2] >> 16, w[5] >> 16) | FILTER_BILINEAR | FULL_BLUR_TXTURE
            self._quad(self._mesh(key, code), w, col=(0, 3, 6, 9), xy=(1, 4, 7, 10), uv=(2, 5, 8, 11),
                       order=QUAD_A, blur_uv=True)
        elif base == 76:                                                # POLY_FT4, point-filtered
            key = k.abr_tex(code, w[2] >> 16, w[4] >> 16) | FILTER_POINT
            self._quad(self._mesh(key, code), w, col=(0,), xy=(1, 3, 5, 7), uv=(2, 4, 6, 8), shade=True,
                       order=QUAD_A)
        elif base == 80:                                                # LINE_G2
            self._line(self._mesh(k.current_abr(code) | LINE_POLYGON, code), w, col=(0, 2), xy=(1, 3))
        elif base in (96, 104, 112, 120):                               # TILE / TILE_1 / _8 / _16
            ww, hh = {104: (1, 1), 112: (8, 8), 120: (16, 16)}.get(base, (None, None))
            if ww is None:
                ww, hh = _s16(w[2]), _s16(w[2] >> 16)
            x0, y0 = _xy(w[1])
            ww = self._tile_fix(x0, y0, ww, hh)
            m = self._mesh(k.current_abr(code), code)
            self._rect(m, x0, y0, ww, hh, _rgb(w[0]), m.alpha, None)
        elif base in (100, 116, 124):                                   # SPRT / SPRT_8 / SPRT_16
            ww, hh = {116: (8, 8), 124: (16, 16)}.get(base, (None, None))
            if ww is None:
                ww, hh = _s16(w[3]), _s16(w[3] >> 16)
            x0, y0 = _xy(w[1])
            ww = self._tile_fix(x0, y0, ww, hh)
            m = self._mesh(k.current_abr_tex(code, w[2] >> 16) | FILTER_BILINEAR, code)
            self._rect(m, x0, y0, ww, hh, _rgb(w[0]), m.shade_alpha(code), _uv(w[2]))
        elif code == 225:                                               # DR_TPAGE
            k.set_tpage(w[0] & 0xFFFF)
        elif code == 228:                                               # DR_AREA
            self._push()
            if (w[1] >> 16) != 0:
                self.dr_x -= GEN_X
                self.dr_y -= GEN_Y
                self.cmds.append(Command("rt_begin"))
            else:
                self.cmds.append(Command("rt_end"))
        elif code == 229:                                               # DR_OFFSET
            self.dr_x = w[1] & 0xFFFF
            self.dr_y = w[1] >> 16
        elif code == 231:                                               # DR_MOVE
            rx, ry = w[1] >> 16, _s16(w[1])
            rw, rh = w[2] >> 16, w[2] & 0xFFFF
            x, y = w[3] >> 16, w[3] & 0xFFFF
            self._push()
            if rx < 320 and ry < 240:
                if self.effnum == EF_SLOW:
                    ry -= 128
                self.cmds.append(Command("screenshot", args=(rx, ry, x, y)))
            else:
                self.cmds.append(Command("move", args=(rx, ry, rw, rh, x, y)))

    @staticmethod
    def _tile_fix(x0: int, y0: int, w: int, h: int) -> int:
        """SFXRender.TILE/SPRT's 80x110 screen-flash fix: with no widescreen only the right tile grows."""
        if w == 80 and h == 110 and y0 in (0, 110) and x0 in (0, 80, 160, 240):
            rightx = {0: 80, 80: 160, 160: 240}.get(x0, 320)
            if rightx == 320 or x0 + w < rightx:
                w += 1
        return w

    # ---- SFXRender.GetMesh
    def _mesh(self, key: int, code: int) -> Mesh:
        bm = blend_mode(key)
        if is_line(key):
            lst = ("line_opa", "line_add", "line_sub")[min(bm, 2)]
        elif is_texture(key):
            if bm == 0:
                lst = "tex_opa"
            elif bm == 1:
                f = key & FILTER_MASK
                # SFX.isDebugFilter is true in the shipping build, so an unflagged texture lands in BL.
                lst = "tex_add_ps" if f == FILTER_POINT else "tex_add_bl"
            else:
                lst = "tex_sub"
        else:
            lst = ("opa", "add", "sub")[min(bm, 2)]
        for m in self.lists[lst]:
            if m.key == key:
                return m
        if not self.pool:
            raise RasterFault("mesh pool exhausted (%d meshes in one frame)" % MESH_MAX)
        m = Mesh(key, code, self.keys.tmp_abr, self.effnum, self.pool.pop(), self.index)
        self.lists[lst].append(m)
        return m

    # ---- SFXRender.PushCommandBuffer
    def _push(self) -> None:
        sub, add = self.sub_order, self.settings["add_order"]
        if sub == 0:
            self._flush("sub", "tex_sub", "line_sub")
        if add == 0:
            self._flush("opa", "tex_opa", "line_opa")
        else:
            self._flush("add", "tex_add_ps", "tex_add_bl", "line_add")
        if sub == 1:
            self._flush("sub", "tex_sub", "line_sub")
        if add == 0:
            self._flush("add", "tex_add_ps", "tex_add_bl", "line_add")
        else:
            self._flush("opa", "tex_opa", "line_opa")
        if sub == 2:
            self._flush("sub", "tex_sub", "line_sub")

    def _flush(self, *names: str) -> None:
        for n in names:
            for m in self.lists[n]:
                self.cmds.append(Command("mesh", m))
            self.lists[n] = []

    # ---- SFXMesh.Poly*/Sprite/Tile/Line* (vertex + index appends, with the C# array limits)
    def _reserve(self, m: Mesh, nv: int, ni: int, ncol: int, ntex: int) -> None:
        if len(m.pos) + nv > VERTICES_MAX or (len(m.tris) * 3 + len(m.lines) * 2) + ni > INDICES_MAX:
            raise RasterFault("IndexOutOfRange: mesh %08X past %d vertices" % (m.key, VERTICES_MAX))
        if self.gpos + nv > POS_MAX or self.gtex + ntex > TEX_MAX or self.gcol + ncol > COL_MAX:
            raise RasterFault("IndexOutOfRange: frame past the shared pos/tex/col arrays (%d/%d/%d)"
                              % (self.gpos + nv, self.gtex + ntex, self.gcol + ncol))
        self.gpos += nv
        self.gtex += ntex
        self.gcol += ncol

    def _verts(self, m: Mesh, w, col, xy, uv, shade: bool, blur_uv: bool) -> int:
        base = len(m.pos)
        a = m.shade_alpha(w[0] >> 24) if shade else m.alpha      # the prim's own code byte
        for i, wi in enumerate(xy):
            x, y = _xy(w[wi])
            m.pos.append((x + self.dr_x, y + self.dr_y, self.z))
            r, g, b = _rgb(w[col[min(i, len(col) - 1)]])
            m.col.append((r, g, b, a))
            if uv:
                u, v = _uv(w[uv[i]])
                if blur_uv:
                    u += 128 if ((m.key >> 16) & 31) != 0 else 0
                    v = 240 - v
                m.uv.append((float(u), float(v)))
            else:
                m.uv.append((0.0, 0.0))
        m.prims += 1
        return base

    def _tri(self, m: Mesh, w, col, xy, uv=None, shade=False) -> None:
        self._reserve(m, 3, 3, len(col), 3 if uv else 0)
        b = self._verts(m, w, col, xy, uv, shade, False)
        m.tris.append((b, b + 1, b + 2))

    def _quad(self, m: Mesh, w, col, xy, order, uv=None, shade=False, blur_uv=False) -> None:
        self._reserve(m, 4, 6, len(col), 4 if uv else 0)
        b = self._verts(m, w, col, xy, uv, shade, blur_uv)
        for t in order:
            m.tris.append((b + t[0], b + t[1], b + t[2]))

    def _line(self, m: Mesh, w, col, xy) -> None:
        self._reserve(m, 2, 2, len(col), 0)
        b = self._verts(m, w, col, xy, None, False, False)
        m.lines.append((b, b + 1))

    def _rect(self, m: Mesh, x0: int, y0: int, w: int, h: int, rgb, a: int, uv) -> None:
        self._reserve(m, 4, 6, 1, 4 if uv else 0)
        b = len(m.pos)
        x, y = x0 + self.dr_x, y0 + self.dr_y
        for dx, dy in ((0, 0), (w, 0), (0, h), (w, h)):
            m.pos.append((x + dx, y + dy, self.z))
            m.col.append(rgb + (a,))
        if uv is None:
            m.uv.extend([(0.0, 0.0)] * 4)
        else:                                       # SFXMesh.Sprite: the UV spans w-1 / h-1
            u, v = uv
            m.uv.extend([(u, v), (u + w - 1.0, v), (u, v + h - 1.0), (u + w - 1.0, v + h - 1.0)])
        m.prims += 1
        for t in QUAD_B:
            m.tris.append((b + t[0], b + t[1], b + t[2]))


# ============================================================== the rasteriser (SFX_*_G[T] shaders, D3D9)
class Target:
    """A colour buffer (+ optional depth) in PSX units * scale: the screen (row 0 at the top), or the
    DR_AREA render target (row 0 = VRAM y 256, the bottom of its y-up ortho)."""

    def __init__(self, w: int, h: int, scale: int, depth: bool, rgb565: bool = False, kind: str = "screen") -> None:
        self.w, self.h, self.scale = w * scale, h * scale, scale
        self.color = np.zeros((self.h, self.w, 3), np.float32)
        self.depth = np.full((self.h, self.w), np.inf, np.float32) if depth else None
        self.rgb565 = rgb565
        self.kind = kind


class Stats:
    def __init__(self) -> None:
        self.mesh_rows: List[dict] = []
        #: cell -> {frame: fragments that changed the SCREEN}; ``gen_cells`` the same for the DR_AREA target
        self.cells: Dict[str, Counter] = defaultdict(Counter)
        self.gen_cells: Dict[str, Counter] = defaultdict(Counter)
        #: "x704_y256@15/GENERATED" -> [mesh renders, first frame, last frame]: where every textured mesh
        #: key actually reads from, counted on EVERY frame (drawn or not)
        self.routes: Dict[str, list] = {}
        #: cells to map on screen ("x704_y384@8", ...): each drawn frame leaves ``watch_masks[cell]`` = the
        #: screen pixels some fragment sampling that cell changed, so a diff can be charged to a cell
        self.watch: set = set()
        self.watch_masks: Dict[str, np.ndarray] = {}

    def route(self, key: int, kind: str, frame: int) -> None:
        tx, ty, tp = (key >> 16) & 0xF, (key >> 20) & 1, (key >> 21) & 3
        name = "x%d_y%d@%d/%s" % (tx * 64, ty * 256, {0: 4, 1: 8}.get(tp, 15), kind)
        r = self.routes.get(name)
        if r is None:
            self.routes[name] = [1, frame, frame]
        else:
            r[0] += 1
            r[2] = frame


def _edge(ax, ay, bx, by, px, py):
    return (bx - ax) * (py - ay) - (by - ay) * (px - ax)


def _top_left(ax, ay, bx, by) -> bool:
    """D3D's top-left rule in y-down raster space with the interior on the E > 0 side."""
    dx, dy = bx - ax, by - ay
    return (dy == 0 and dx > 0) or dy < 0


def _sample(tex: np.ndarray, fx: np.ndarray, fy: np.ndarray, bilinear: bool) -> np.ndarray:
    """Clamp-to-edge sample of an (H, W, C) float array at texel-space coords (centres at +0.5)."""
    hgt, wid = tex.shape[:2]
    if not bilinear:
        xi = np.clip(np.floor(fx).astype(np.int64), 0, wid - 1)
        yi = np.clip(np.floor(fy).astype(np.int64), 0, hgt - 1)
        return tex[yi, xi]
    x, y = fx - 0.5, fy - 0.5
    x0, y0 = np.floor(x), np.floor(y)
    ax, ay = (x - x0)[:, None], (y - y0)[:, None]
    x0i = np.clip(x0.astype(np.int64), 0, wid - 1)
    y0i = np.clip(y0.astype(np.int64), 0, hgt - 1)
    x1i = np.clip(x0.astype(np.int64) + 1, 0, wid - 1)
    y1i = np.clip(y0.astype(np.int64) + 1, 0, hgt - 1)
    top = tex[y0i, x0i] * (1 - ax) + tex[y0i, x1i] * ax
    bot = tex[y1i, x0i] * (1 - ax) + tex[y1i, x1i] * ax
    return top * (1 - ay) + bot * ay


class TextureSource:
    """What one textured mesh samples: an (H, W, 4) float array, its row orientation, and TexParam."""
    __slots__ = ("kind", "tex", "rows_from_top", "param", "bilinear", "cell_of")

    def __init__(self, kind, tex, rows_from_top, param, bilinear, cell_of=None):
        self.kind, self.tex, self.rows_from_top = kind, tex, rows_from_top
        self.param, self.bilinear, self.cell_of = param, bilinear, cell_of


class Renderer:
    """SFXRender.Render / Runtime.Render over one frame's command buffer, into the headless screen."""

    def __init__(self, effnum: int, settings: dict, cache: TextureCache, scale: int = 1) -> None:
        self.effnum = effnum
        self.settings = settings
        self.cache = cache
        self.scale = scale
        self.color = COLOR_DATA[settings["col_intensity"]]
        self.threshold = 0.05 if settings["col_threshold"] else 0.0295
        self.gen = Target(GEN_W, GEN_H, 1, depth=False, rgb565=True, kind="gen")
        self.gen_created = False                    # PSXTextureMgr.isCreateGenTexture
        self.gen_first_frame: Optional[int] = None
        self.bg_key = 0
        self.prev_screen: Optional[np.ndarray] = None     # the blur texture (previous frame)
        self.screen_shot = 0

    def render(self, cmds: Sequence[Command], frame: int, draw: bool, stats: Optional[Stats] = None) -> Optional[Target]:
        """Execute one frame. ``draw=False`` still runs moves, texture lookups and render-to-texture --
        the cache and the generated texture carry state from frame to frame -- but skips the screen."""
        screen = Target(SCREEN_W, SCREEN_H, self.scale, depth=True) if draw else None
        if screen is not None and stats is not None and stats.watch:
            stats.watch_masks = {c: np.zeros((screen.h, screen.w), bool) for c in stats.watch}
        target = screen
        rt = False
        for i, c in enumerate(cmds):
            if c.kind == "move":
                rx, ry, rw, rh, x, y = c.args
                self.move_image(rx, ry, rw, rh, x, y)
            elif c.kind == "screenshot":
                self.screen_shot += 1
            elif c.kind == "rt_begin":
                if not self.gen_created:
                    self.gen.color[:] = 0.0
                target, rt = self.gen, True
            elif c.kind == "rt_end":
                self.gen_created = True
                if self.gen_first_frame is None:
                    self.gen_first_frame = frame
                target, rt = screen, False
            elif c.kind == "mesh":
                m = c.mesh
                src = self.texture_for(m) if is_texture(m.key) else None
                if stats is not None and is_texture(m.key):
                    stats.route(m.key, src.kind if src else "NULL", frame)
                if is_texture(m.key) and src is None:
                    if stats is not None and draw:
                        stats.mesh_rows.append(self._row(frame, i, m, None, 0, 0, rt))
                    continue
                if target is None:
                    continue
                cov, vis = self.draw_mesh(target, m, src, stats if (draw or rt) else None, frame)
                if stats is not None and (draw or rt):
                    stats.mesh_rows.append(self._row(frame, i, m, src, cov, vis, rt))
        if screen is not None:
            self.prev_screen = screen.color.copy()
        return screen

    @staticmethod
    def _row(frame, i, m: Mesh, src, cov, vis, rt) -> dict:
        return {"frame": frame, "index": i, "key": "%08X" % m.key, "blend": ("opa", "add", "sub")[min(m.blend, 2)],
                "kind": src.kind if src else (KIND_NONE if not is_texture(m.key) else "NULL"), "tris": len(m.tris),
                "lines": len(m.lines), "prims": m.prims, "fragments": int(cov), "visible": int(vis),
                "target": "gen" if rt else "screen"}

    # ---- PSXTextureMgr.MoveImage(rx, ry, rw, rh, x, y) -- SFXMoveImage.Render
    def move_image(self, rx, ry, rw, rh, x, y) -> None:
        flat = self.cache.flat
        for i in range(rh):
            d = ((i + y) << 10) + x
            s = ((i + ry) << 10) + rx
            if rw <= 0:
                break
            if min(d, s) < 0 or max(d, s) + rw > flat.size:
                raise RasterFault("IndexOutOfRange in MoveImage (%d,%d)->(%d,%d)" % (rx, ry, x, y))
            flat[d:d + rw] = flat[s:s + rw].copy()
        self.cache.clear_key(x, y)

    # ---- SFXMesh.GetTexture
    def texture_for(self, m: Mesh) -> Optional[TextureSource]:
        key = m.key
        tkey = key & TEX_KEY_MASK
        bil = (key & FILTER_MASK) != FILTER_POINT                 # isDebugFilter: all but POINT are bilinear
        if texture_mode(key) != 2:
            rgba = self.cache.get(key)
            if rgba is None:
                return None
            return TextureSource(KIND_IMAGE, rgba, False, (0.5, 0.5, 256.0, 256.0), bil,
                                 self._cell_fn(key))
        if is_blur_texture(tkey):
            if key & FULL_BLUR_TXTURE:
                param = (0.5, 0.5, 320.0, 240.0)
            else:
                param = (0.5, -240.0, 320.0, -240.0)
            return TextureSource(KIND_BLUR, self._blur(), True, param, bil)
        if (key & 0x1F0000) == self.bg_key:
            # The battle-ground capture. Headless has no battle scene: PSXTextureMgr.CaptureBG with no
            # ground mesh clears to transparent black, which is what this returns.
            return TextureSource(KIND_BACKGROUND, np.zeros((256, 256, 4), np.float32), False,
                                 (0.5, 0.5, 256.0, 256.0), bil)
        if self.effnum == EF_STOP and tkey == 0x578000:
            rgba = self.cache.get(key)
            if rgba is None:
                return None
            return TextureSource(KIND_IMAGE, rgba, False, (0.5, 0.5, 256.0, 256.0), bil,
                                 self._cell_fn(key))
        if self.gen_created:
            gen = np.concatenate([self.gen.color, np.ones(self.gen.color.shape[:2] + (1,), np.float32)], axis=-1)
            x = ((key >> 16) & 0xF) * 64 - GEN_X + 0.5             # SFXKey.GetPositionX - GEN_TEXTURE_X + 0.5
            return TextureSource(KIND_GENERATED, gen, False, (x, 0.5, float(GEN_W), float(GEN_H)), bil)
        rgba = self.cache.get(key)
        if rgba is None:
            return None
        return TextureSource(KIND_IMAGE, rgba, False, (0.5, 0.5, 256.0, 256.0), bil,
                             self._cell_fn(key))

    def _blur(self) -> np.ndarray:
        if self.prev_screen is None:
            img = np.zeros((SCREEN_H * self.scale, SCREEN_W * self.scale, 3), np.float32)
        else:
            img = self.prev_screen
        return np.concatenate([img, np.ones(img.shape[:2] + (1,), np.float32)], axis=-1)

    @staticmethod
    def _cell_fn(key: int):
        tx, ty, tp = (key >> 16) & 0xF, (key >> 20) & 1, (key >> 21) & 3
        div = {0: 4, 1: 2}.get(tp, 1)
        bpp = {0: 4, 1: 8}.get(tp, 15)

        def cell(u: np.ndarray, v: np.ndarray) -> np.ndarray:
            x = tx * 64 + np.clip(u, 0, 255).astype(np.int64) // div
            y = ty * 256 + np.clip(v, 0, 255).astype(np.int64)
            return (x // 64 * 64) * 10000 + (y // 128 * 128) * 10 + {4: 0, 8: 1, 15: 2}[bpp]
        return cell

    # ---- the draw
    def draw_mesh(self, t: Target, m: Mesh, src: Optional[TextureSource], stats: Optional[Stats], frame: int):
        if not m.pos:
            return 0, 0
        pos = np.asarray(m.pos, np.float64)
        col = np.asarray(m.col, np.float64) / 255.0
        # SFX_*_G[T] vertex program: oD0.rgb = vcol.rgb * _Color * vcol.a, saturated (vs_2_0 colour output)
        vrgb = np.clip(col[:, :3] * self.color * col[:, 3:4], 0.0, 1.0)
        uv = np.asarray(m.uv, np.float64)
        cov = vis = 0
        for tri in m.tris:
            c, v = self._tri(t, m, pos[list(tri)], vrgb[list(tri)], uv[list(tri)], src, stats, frame)
            cov += c
            vis += v
        for ln in m.lines:
            c, v = self._line(t, m, pos[list(ln)], vrgb[list(ln)])
            cov += c
            vis += v
        return cov, vis

    def _tri(self, t: Target, m: Mesh, P, RGB, UV, src, stats, frame):
        s = t.scale
        X, Y = P[:, 0] * s, P[:, 1] * s
        if _edge(X[0], Y[0], X[1], Y[1], X[2], Y[2]) < 0:
            X, Y, RGB, UV = X[[0, 2, 1]], Y[[0, 2, 1]], RGB[[0, 2, 1]], UV[[0, 2, 1]]
        area = _edge(X[0], Y[0], X[1], Y[1], X[2], Y[2])
        if area <= 0:
            return 0, 0
        x0 = max(0, int(np.floor(X.min())))
        x1 = min(t.w, int(np.ceil(X.max())) + 1)
        y0 = max(0, int(np.floor(Y.min())))
        y1 = min(t.h, int(np.ceil(Y.max())) + 1)
        if x0 >= x1 or y0 >= y1:
            return 0, 0
        px = np.arange(x0, x1) + 0.5
        py = np.arange(y0, y1) + 0.5
        gx, gy = np.meshgrid(px, py)
        e0 = _edge(X[1], Y[1], X[2], Y[2], gx, gy)       # opposite v0
        e1 = _edge(X[2], Y[2], X[0], Y[0], gx, gy)       # opposite v1
        e2 = _edge(X[0], Y[0], X[1], Y[1], gx, gy)       # opposite v2
        inside = ((e0 > 0) | ((e0 == 0) & _top_left(X[1], Y[1], X[2], Y[2]))) & \
                 ((e1 > 0) | ((e1 == 0) & _top_left(X[2], Y[2], X[0], Y[0]))) & \
                 ((e2 > 0) | ((e2 == 0) & _top_left(X[0], Y[0], X[1], Y[1])))
        if not inside.any():
            return 0, 0
        jj, ii = np.nonzero(inside)
        l0 = e0[jj, ii] / area
        l1 = e1[jj, ii] / area
        l2 = 1.0 - l0 - l1
        ry, rx = jj + y0, ii + x0
        z = P[0, 2]
        if t.depth is not None:
            ok = t.depth[ry, rx] >= z                    # ZTest LEqual
            if not ok.any():
                return 0, 0
            ry, rx, l0, l1, l2 = ry[ok], rx[ok], l0[ok], l1[ok], l2[ok]
        rgb = l0[:, None] * RGB[0] + l1[:, None] * RGB[1] + l2[:, None] * RGB[2]
        alpha = np.ones(len(ry))
        cells = None
        if src is not None:
            u = l0 * UV[0, 0] + l1 * UV[1, 0] + l2 * UV[2, 0]
            v = l0 * UV[0, 1] + l1 * UV[1, 1] + l2 * UV[2, 1]
            px_, py_, pz, pw = src.param
            s_ = (u + px_) / pz                          # oT0 = (uv + _TexParam.xy) / _TexParam.zw
            t_ = (v + py_) / pw
            hgt, wid = src.tex.shape[:2]
            fx = s_ * wid
            fy = (1.0 - t_) * hgt if src.rows_from_top else t_ * hgt
            texel = _sample(src.tex, fx, fy, src.bilinear)
            rgb = rgb * texel[:, :3]
            alpha = texel[:, 3]
            if src.cell_of is not None:
                cells = src.cell_of(np.floor(fx), np.floor(fy))
            if m.shader == 0:                            # SFX_OPA_GT: texkill when tex.a < _Threshold
                keep = alpha - self.threshold >= 0
                ry, rx, rgb, alpha = ry[keep], rx[keep], rgb[keep], alpha[keep]
                if cells is not None:
                    cells = cells[keep]
                if not len(ry):
                    return 0, 0
        before = t.color[ry, rx].copy()
        bm = m.shader % 3
        if bm == 0:                                      # Blend SrcAlpha OneMinusSrcAlpha (ZWrite on)
            out = rgb * alpha[:, None] + before * (1.0 - alpha[:, None])
            if t.depth is not None:
                t.depth[ry, rx] = z
        elif bm == 1:                                    # Blend SrcAlpha One
            out = before + rgb * alpha[:, None]
        else:                                            # Blend One One, BlendOp RevSub
            out = before - rgb
        out = np.clip(out, 0.0, 1.0)
        if t.rgb565:
            out = np.stack([np.round(out[:, 0] * 31) / 31, np.round(out[:, 1] * 63) / 63,
                            np.round(out[:, 2] * 31) / 31], axis=-1)
        else:
            out = np.round(out * 255.0) / 255.0          # an 8-bit backbuffer
        t.color[ry, rx] = out
        changed = np.any(np.abs(out - before) >= 0.5 / 255.0, axis=-1)
        if stats is not None and cells is not None and changed.any():
            for cid, n in zip(*np.unique(cells[changed], return_counts=True)):
                cx, rest = divmod(int(cid), 10000)
                cy, b = divmod(rest, 10)
                book = stats.cells if t.kind == "screen" else stats.gen_cells
                name = "x%d_y%d@%d" % (cx, cy, (4, 8, 15)[b])
                book[name][frame] += int(n)
                if t.kind == "screen" and name in stats.watch_masks:
                    hit = changed & (cells == cid)
                    stats.watch_masks[name][ry[hit], rx[hit]] = True
        return len(ry), int(changed.sum())

    def _line(self, t: Target, m: Mesh, P, RGB):
        s = t.scale
        (xa, ya), (xb, yb) = P[0, :2] * s, P[1, :2] * s
        n = int(max(abs(xb - xa), abs(yb - ya)))
        if n == 0:
            return 0, 0
        f = np.arange(n) / n                              # the last pixel is not drawn (D3D9 lines)
        rx = np.floor(xa + (xb - xa) * f + 0.5).astype(np.int64)
        ry = np.floor(ya + (yb - ya) * f + 0.5).astype(np.int64)
        ok = (rx >= 0) & (rx < t.w) & (ry >= 0) & (ry < t.h)
        rx, ry, f = rx[ok], ry[ok], f[ok]
        z = P[0, 2]
        if t.depth is not None:
            ok = t.depth[ry, rx] >= z
            rx, ry, f = rx[ok], ry[ok], f[ok]
        if not len(rx):
            return 0, 0
        rgb = RGB[0] * (1 - f[:, None]) + RGB[1] * f[:, None]
        before = t.color[ry, rx].copy()
        bm = m.shader % 3
        out = rgb if bm == 0 else (before + rgb if bm == 1 else before - rgb)
        if bm == 0 and t.depth is not None:
            t.depth[ry, rx] = z
        out = np.round(np.clip(out, 0.0, 1.0) * 255.0) / 255.0
        t.color[ry, rx] = out
        return len(rx), int(np.any(np.abs(out - before) >= 0.5 / 255.0, axis=-1).sum())


# ============================================================== the plugin run (sfx_host's loop, render-timed)
class RasterHost(H.Host):
    """``sfx_host.Host`` with Memoria's VRAM bookkeeping: the 0x00FF fill PSXTextureMgr.InitOnce writes,
    ClearKey on every upload/move, Devour's skipped move, and the code-120 background-capture request."""

    def __init__(self, effnum: int, **kw) -> None:
        super().__init__(**kw)
        self.effnum = effnum
        self.vram.mem[0::2] = b"\xff" * (len(self.vram.mem) // 2)        # originalVram[i] = 255
        self.np_vram = np.frombuffer(self.vram.mem, dtype="<u2").reshape(H.Vram.H, H.Vram.W)
        self.cache = TextureCache(self.np_vram)
        self.bg_capture: Optional[Tuple[int, ...]] = None

    def _dispatch(self, full, a0, a1, a2, a3, p):
        code = (full >> 24) & 0xFF
        if code == 102 and self.effnum == EF_DEVOUR:     # PSXTextureMgr.MoveImage: Devour only flags a capture
            self.codes[code] += 1
            self.vram_ops.append((self.frame, "move-skipped", (a0, a1)))
            return 0
        if code == 120 and p:                            # BattleCallbackDummy: isBgCapture + bgParam
            self.bg_capture = struct.unpack("<7i", self._get(p, 28))
        r = super()._dispatch(full, a0, a1, a2, a3, p)
        if code == 100:
            self.cache.clear_key(a0, a1)
        elif code == 102:
            self.cache.clear_key(a0, a1)
        return r


def parse_frames(spec: Optional[str]) -> Optional[set]:
    if not spec:
        return None
    out = set()
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:                             # a-b, or a-b:step
            rng, _, step = part.partition(":")
            a, b = rng.split("-", 1)
            out.update(range(int(a), int(b) + 1, int(step or 1)))
        elif part:
            out.add(int(part))
    return out


def run(bin_dir: Path, blob: bytes, effnum: int, *, frames: Optional[set] = None, scale: int = 1,
        max_frames: int = 8000, on_frame=None, keep_prims: bool = False, watch: Iterable[str] = ()) -> dict:
    """Play ``blob`` through the plugin and render it. ``frames`` = the frames to draw (None = every one).

    ``on_frame(frame, screen_target_or_None, cmds, stats)`` is called after each frame. ``watch`` names
    cells (``"x704_y384@8"``) whose screen footprint ``stats.watch_masks`` holds for each drawn frame."""
    H._install_no_dialog(bin_dir)
    dll = C.CDLL(str(bin_dir / H.PLUGIN))
    host = RasterHost(effnum, mode="rework")
    CB = C.CFUNCTYPE(C.c_int32, C.c_int32, C.c_int32, C.c_int32, C.c_int32, C.c_int32, C.c_void_p)
    cb = CB(host.callback)
    dll.SFX_InitSystem.argtypes = [CB]
    dll.SFX_InitBattle.argtypes = [C.c_void_p]
    dll.SFX_Play.argtypes = [C.c_int32, C.c_void_p, C.c_int32, C.c_void_p]
    dll.SFX_Update.argtypes = [C.POINTER(C.c_int32)]
    dll.SFX_Update.restype = C.c_bool
    dll.SFX_BeginRender.restype = C.c_bool
    dll.SFX_GetPrim.argtypes = [C.POINTER(C.c_int32)]
    dll.SFX_GetPrim.restype = C.c_void_p
    dll.SFX_UpdateCamera.argtypes = [C.c_int32]
    dll.SFX_UpdateCamera.restype = C.c_void_p
    dll.SFX_InitSystem(cb)
    param = H.build_init_param()
    pbuf = (C.c_ubyte * len(param)).from_buffer(param)
    dll.SFX_InitBattle(C.addressof(pbuf))
    req = H.build_request()
    rbuf = (C.c_ubyte * len(req)).from_buffer(req)
    bbuf = (C.c_ubyte * len(blob)).from_buffer_copy(blob)
    dll.SFX_Play(effnum, C.addressof(bbuf), len(blob), C.addressof(rbuf))

    settings = play_settings(effnum)
    keys = KeyState()
    builder = FrameBuilder(effnum, settings, keys)
    renderer = Renderer(effnum, settings, host.cache, scale)
    stats = Stats()
    stats.watch = set(watch)
    faults: List[str] = []
    per_frame: List[dict] = []
    prim_log: Dict[int, list] = {}
    frame = C.c_int32(0)
    ended = None
    for n in range(max_frames):
        host.frame = n + 1
        running = dll.SFX_Update(C.byref(frame))
        dll.SFX_LateUpdate()
        prims: List[Tuple[int, bytes, int]] = []
        if dll.SFX_BeginRender():
            while True:
                otz = C.c_int32(0)
                ptr = dll.SFX_GetPrim(C.byref(otz))
                if not ptr:
                    break
                ln = C.c_ubyte.from_address(ptr + 3).value
                code = C.c_ubyte.from_address(ptr + 7).value
                prims.append((code, C.string_at(ptr + 4, ln * 4), otz.value))
        f = frame.value
        if keep_prims:
            prim_log[f] = prims
        cmds, fl = builder.build(prims, f)
        faults.extend(fl)
        if host.bg_capture is not None:                  # PSXTextureMgr.CaptureBG at Render
            bp = host.bg_capture
            renderer.bg_key = (bp[1] >> 8 << 20) | (bp[0] >> 6 << 16)
            host.bg_capture = None
        want = frames is None or f in frames
        draw = want or (frames is not None and (f + 1) in frames)     # the blur texture is the frame before
        try:
            screen = renderer.render(cmds, f, draw, stats)
        except RasterFault as e:
            faults.append("frame %d render: %s" % (f, e))
            screen = None
        per_frame.append({"frame": f, "prims": len(prims), "meshes": sum(1 for c in cmds if c.kind == "mesh"),
                          "commands": len(cmds)})
        if on_frame is not None:
            on_frame(f, screen if want else None, cmds, stats)
        dll.SFX_UpdateCamera(0)
        if not running:
            ended = n
            break
    return {"effect": effnum, "settings": settings, "frames": len(per_frame), "ended_at": ended,
            "faults": faults, "per_frame": per_frame, "stats": stats, "texture_cache": {
                "generated": host.cache.generated, "refused_full": host.cache.full},
            "gen_texture_used": renderer.gen_created, "gen_texture_first_frame": renderer.gen_first_frame,
            "screenshots": renderer.screen_shot,
            "unported_special": UNPORTED_SPECIALS.get(effnum), "prim_log": prim_log, "host": host}


# ============================================================== output
def save_png(t: Target, path: Path) -> None:
    from PIL import Image
    path = H._refuse_repo_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.round(np.clip(t.color, 0, 1) * 255).astype(np.uint8), "RGB").save(path)


def visible_cells(stats: Stats, gen: bool = False) -> Dict[str, dict]:
    """cell -> {pixels, frames [first, last], n_frames} -- fragments that changed the screen (or, with
    ``gen``, the DR_AREA render target)."""
    out = {}
    for cell, frames in sorted((stats.gen_cells if gen else stats.cells).items()):
        fs = sorted(frames)
        out[cell] = {"pixels": int(sum(frames.values())), "frames": [fs[0], fs[-1]], "n_frames": len(fs)}
    return out


def mesh_summary(stats: Stats) -> Dict[str, dict]:
    agg: Dict[Tuple[str, str], dict] = {}
    for r in stats.mesh_rows:
        k = (r["key"], r["kind"])
        a = agg.setdefault(k, {"key": r["key"], "kind": r["kind"], "blend": r["blend"], "frames": 0,
                               "fragments": 0, "visible": 0, "first": r["frame"], "last": r["frame"],
                               "targets": set()})
        a["frames"] += 1
        a["fragments"] += r["fragments"]
        a["visible"] += r["visible"]
        a["last"] = r["frame"]
        a["targets"].add(r["target"])
    return {"%s/%s" % k: dict(v, targets=sorted(v["targets"])) for k, v in agg.items()}


# ============================================================== calibration vs an in-game s48 probe log
def read_probe_log(path: Path, effnum: int) -> List[dict]:
    """Split an s48 log into casts of ``effnum``: [{frame: {"prims": [(index, code, otz, x, y)],
    "states": [(index, code, ...)], "meshes": [(index, key, tris)]}}]. A frame number that goes
    backwards starts a new cast; MESH rows repeat once per game frame and are de-duplicated."""
    casts: List[dict] = []
    cur: Optional[dict] = None
    last = -1
    eff = str(effnum)
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if not line.startswith(("PRIM,", "STATE,", "MESH,")):
                continue
            parts = line.rstrip("\n").split(",")
            kind = parts[0]
            if len(parts) < 6 or parts[1] != eff:
                continue
            fr = int(parts[2])
            if cur is None or fr < last:             # the frame went backwards: a new cast (or the
                cur = {}                             # SFXRework set-up pre-run before the real one)
                casts.append(cur)
            last = fr
            row = cur.setdefault(fr, {"prims": [], "states": [], "meshes": [], "mesh_seen": set()})
            if kind == "PRIM":
                row["prims"].append((int(parts[3]), int(parts[4]), -float(parts[6]), int(parts[7]), int(parts[8])))
            elif kind == "STATE":
                row["states"].append((int(parts[3]), int(parts[4])) + tuple(parts[5:]))
            else:
                key = (int(parts[3]), parts[4].upper(), int(parts[6]))
                if key not in row["mesh_seen"]:
                    row["mesh_seen"].add(key)
                    row["meshes"].append(key)
    return casts


def _headless_prim_rows(prims) -> Tuple[list, list]:
    """The headless prim list in the probe's row shape: PRIM (index, code, otz, x0, y0), STATE (index, code)."""
    pr, st = [], []
    for i, (code, body, otz) in enumerate(prims):
        if code >= 0xE0:
            st.append((i, code))
            continue
        if len(body) >= 8:
            x, y = _xy(struct.unpack_from("<I", body, 4)[0])
        else:
            x = y = 0
        pr.append((i, code, float(otz), x, y))
    return pr, st


def calibrate(bin_dir: Path, blob: bytes, effnum: int, log: Path, max_frames: int = 8000,
              xy_detail: bool = False) -> dict:
    """RX1 (prim stream) and RX2 (command buffer) per frame, headless vs every cast in ``log``.

    ``xy_detail`` adds ``xy_delta``: in-game minus headless first vertex, ``"[dx, dy]" -> count``, over
    the input-matched frames (the probe logs ``v + drOffset``, so widescreen shows as dx = +35)."""
    casts = read_probe_log(log, effnum)
    cmd_by_frame: Dict[int, list] = {}

    def keep(f, screen, cmds, stats):
        cmd_by_frame[f] = [(i, "%08X" % c.mesh.key, len(c.mesh.tris)) for i, c in enumerate(cmds) if c.kind == "mesh"]

    res = run(bin_dir, blob, effnum, frames=set(), max_frames=max_frames, on_frame=keep, keep_prims=True)
    out = {"effect": effnum, "log": str(log), "headless_frames": res["frames"], "casts": []}
    for ci, cast in enumerate(casts):
        rep = {"cast": ci, "frames": len(cast), "rx1": Counter(), "rx2": Counter(), "rx1_first_miss": None,
               "rx2_first_miss": None, "otz_equal": 0, "otz_total": 0, "xy_equal": 0, "xy_delta": Counter()}
        for fr in sorted(cast):
            g = cast[fr]
            hp = res["prim_log"].get(fr)
            if hp is None:
                rep["rx1"]["no_headless_frame"] += 1
                continue
            pr, st = _headless_prim_rows(hp)
            seq_g = sorted([(i, c) for i, c, *_ in g["prims"]] + [(s[0], s[1]) for s in g["states"]])
            seq_h = sorted([(i, c) for i, c, *_ in pr] + st)
            same_input = seq_g == seq_h
            if same_input:
                rep["rx1"]["match"] += 1
                for a, b in zip(sorted(g["prims"]), sorted(pr)):
                    rep["otz_total"] += 1
                    rep["otz_equal"] += int(abs(a[2] - b[2]) < 1e-6)
                    rep["xy_equal"] += int(a[3:] == b[3:])
                    rep["xy_delta"][json.dumps([a[3] - b[3], a[4] - b[4]])] += 1
            else:
                rep["rx1"]["differ"] += 1
                if rep["rx1_first_miss"] is None:
                    rep["rx1_first_miss"] = {"frame": fr, "ingame": len(seq_g), "headless": len(seq_h)}
            if g["meshes"]:
                # RX2 judges the BATCHING port, so it is scored only where RX1 says both sides fed the
                # renderer the same prim sequence; the other frames are counted apart.
                hm = cmd_by_frame.get(fr, [])
                gm = [(i, k, t) for i, k, t in g["meshes"]]
                bucket = "match" if gm == hm else "differ"
                if not same_input:
                    rep["rx2"]["unscored_" + bucket] += 1
                    continue
                rep["rx2"][bucket] += 1
                if bucket == "differ" and rep["rx2_first_miss"] is None:
                    rep["rx2_first_miss"] = {"frame": fr, "ingame": gm[:8], "headless": hm[:8]}
        rep["rx1"], rep["rx2"] = dict(rep["rx1"]), dict(rep["rx2"])
        rep["xy_delta"] = dict(rep["xy_delta"]) if xy_detail else None
        out["casts"].append(rep)
    return out


# ============================================================== diff: does an edit reach the screen?
def diff_frames(dir_a: Path, dir_b: Path, out: Path) -> dict:
    """Per-frame pixel diff of two ``run`` folders: changed pixels (any channel off by more than one
    8-bit step), the largest channel difference, and an amplified |A-B| PNG per frame that changed."""
    from PIL import Image
    rows = {}
    for pa in sorted(Path(dir_a).glob("f*.png")):
        pb = Path(dir_b) / pa.name
        if not pb.exists():
            continue
        A = np.asarray(Image.open(pa).convert("RGB"), np.int16)
        B = np.asarray(Image.open(pb).convert("RGB"), np.int16)
        d = np.abs(A - B)
        changed = int((d.max(axis=-1) > 1).sum())
        f = int(pa.stem[1:])
        rows[f] = {"changed_px": changed, "max_diff": int(d.max()), "of": int(A.shape[0] * A.shape[1])}
        if changed:
            amp = np.clip(d * 4, 0, 255).astype(np.uint8)
            p = H._refuse_repo_path(Path(out) / ("diff_%s" % pa.name))
            p.parent.mkdir(parents=True, exist_ok=True)
            Image.fromarray(amp, "RGB").save(p)
    return rows


def diff_main(a) -> int:
    import subprocess
    out = H._refuse_repo_path(Path(a.out))
    me = str(Path(__file__).resolve())
    sides = {}
    for tag, cont in (("a", a.a), ("b", a.b)):
        cmd = [sys.executable, "-I", me, "run", "--ef", str(a.ef), "--frames", a.frames, "--scale", str(a.scale),
               "--out", str(out / tag)]
        if cont != "stock":
            cmd += ["--container", cont]
        if a.bin:
            cmd += ["--bin", a.bin]
        cp = subprocess.run(cmd, capture_output=True, text=True)
        if cp.returncode != 0:
            print(cp.stdout[-2000:], cp.stderr[-2000:])
            return 1
        sides[tag] = json.loads((out / tag / "summary.json").read_text(encoding="utf-8"))
    rows = diff_frames(out / "a", out / "b", out)
    cells_a, cells_b = sides["a"]["visible_cells"], sides["b"]["visible_cells"]
    cell_delta = {c: {"a": cells_a.get(c, {}).get("pixels", 0), "b": cells_b.get(c, {}).get("pixels", 0)}
                  for c in sorted(set(cells_a) | set(cells_b))
                  if cells_a.get(c, {}).get("pixels", 0) != cells_b.get(c, {}).get("pixels", 0)}
    doc = {"effect": a.ef, "a": a.a, "b": a.b, "frames": rows, "cells_that_moved": cell_delta,
           "frames_changed": sum(1 for r in rows.values() if r["changed_px"])}
    (out / "diff.json").write_text(json.dumps(doc, indent=1), encoding="utf-8")
    print("ef%03d: %d of %d frames differ -> %s" % (a.ef, doc["frames_changed"], len(rows), out))
    for f, r in sorted(rows.items()):
        if r["changed_px"]:
            print("  f%-5d %7d px changed (max channel diff %d)" % (f, r["changed_px"], r["max_diff"]))
    return 0


# ============================================================== routes: the census of texture sources
def routes_main(a) -> int:
    """Run every container with ``--no-draw`` in its own process; tabulate, per effect, whether it
    renders into the DR_AREA target and where each textured key reads from (IMAGE = VRAM, BLUR = the
    previous frame, GENERATED = the render target, BACKGROUND = the ground capture)."""
    import subprocess
    from concurrent.futures import ThreadPoolExecutor
    out = H._refuse_repo_path(Path(a.out))
    out.mkdir(parents=True, exist_ok=True)
    ids = [int(x) for x in a.only.split(",")] if a.only else H.corpus_ids()
    me = str(Path(__file__).resolve())

    def one(e):
        dest = out / ("ef%03d" % e)
        cmd = [sys.executable, "-I", me, "run", "--ef", str(e), "--no-draw", "--out", str(dest)]
        if a.bin:
            cmd += ["--bin", a.bin]
        try:
            cp = subprocess.run(cmd, capture_output=True, text=True, timeout=1200)
        except subprocess.TimeoutExpired:
            return e, {"error": "timeout"}
        if cp.returncode != 0:
            return e, {"error": (cp.stderr or cp.stdout)[-300:]}
        return e, json.loads((dest / "summary.json").read_text(encoding="utf-8"))

    rows = {}
    with ThreadPoolExecutor(max_workers=max(1, a.jobs)) as ex:
        for e, d in ex.map(one, ids):
            if "error" in d:
                rows["ef%03d" % e] = {"error": d["error"]}
                continue
            rows["ef%03d" % e] = {"frames": d["frames"], "faults": d["faults"], "dr_area": d["gen_texture_used"],
                                  "dr_area_first_frame": d.get("gen_texture_first_frame"),
                                  "texture_cache": d["texture_cache"], "routes": d["routes"]}
    doc = {"containers": len(rows), "rows": rows}
    (out / "routes.json").write_text(json.dumps(doc, indent=1), encoding="utf-8")
    with open(out / "routes.tsv", "w", encoding="utf-8") as fh:
        fh.write("effect\tdr_area\tfirst_rt_frame\tpage\tkind\tmesh_renders\tframes\n")
        for e, r in sorted(rows.items()):
            for page, (n, f0, f1) in sorted(r.get("routes", {}).items()):
                pg, kind = page.split("/")
                fh.write("%s\t%s\t%s\t%s\t%s\t%d\t%d-%d\n" % (e, r["dr_area"], r["dr_area_first_frame"], pg, kind, n, f0, f1))
    errs = sum(1 for r in rows.values() if "error" in r)
    rt = sum(1 for r in rows.values() if r.get("dr_area"))
    print("routes: %d containers, %d errors, %d render into DR_AREA -> %s" % (len(rows), errs, rt, out))
    return 0


# ============================================================== CLI
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    rp = sub.add_parser("run", help="render a container's frames")
    rp.add_argument("--ef", type=int, required=True)
    rp.add_argument("--container")
    rp.add_argument("--from-install", action="store_true")
    rp.add_argument("--game")
    rp.add_argument("--bin")
    rp.add_argument("--frames", help="e.g. 82,150-160 (default: every frame, no PNGs)")
    rp.add_argument("--scale", type=int, default=1)
    rp.add_argument("--out", help="output folder (SCRATCH only)")
    rp.add_argument("--tag", default="", help="a suffix for the output folder")
    rp.add_argument("--max-frames", type=int, default=8000)
    rp.add_argument("--no-draw", action="store_true", help="run the batching and texture routing only (fast)")
    dp = sub.add_parser("diff", help="render two containers (each in its own process) and diff the frames")
    dp.add_argument("--ef", type=int, required=True)
    dp.add_argument("--a", default="stock", help="container A (default: the stock corpus file)")
    dp.add_argument("--b", required=True, help="container B")
    dp.add_argument("--frames", required=True)
    dp.add_argument("--scale", type=int, default=1)
    dp.add_argument("--out", required=True, help="output folder (SCRATCH only)")
    dp.add_argument("--bin")
    op = sub.add_parser("routes", help="every corpus container: where each texture key really reads from")
    op.add_argument("--jobs", type=int, default=6)
    op.add_argument("--only", help="comma-separated effect ids")
    op.add_argument("--out", default=str(RASTER_DIR / "routes"))
    op.add_argument("--bin")
    cp = sub.add_parser("calibrate", help="the RX gates vs an in-game s48 probe log")
    cp.add_argument("--ef", type=int, required=True)
    cp.add_argument("--log", required=True)
    cp.add_argument("--container")
    cp.add_argument("--from-install", action="store_true")
    cp.add_argument("--game")
    cp.add_argument("--bin")
    cp.add_argument("--json")
    a = ap.parse_args(argv)
    if a.cmd == "diff":
        return diff_main(a)
    if a.cmd == "routes":
        return routes_main(a)
    blob, source, _ = H.load_container(a.ef, a.container, a.from_install, a.game)
    bdir, sha = H.resolve_bin(a.bin, a.game)
    if a.cmd == "calibrate":
        rep = calibrate(bdir, blob, a.ef, Path(a.log))
        print(json.dumps(rep, indent=1, default=str))
        if a.json:
            p = H._refuse_repo_path(Path(a.json))
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(rep, indent=1, default=str), encoding="utf-8")
        return 0
    frames = parse_frames(a.frames)
    out = Path(a.out) if a.out else RASTER_DIR / ("ef%03d%s" % (a.ef, ("-" + a.tag) if a.tag else ""))
    out = H._refuse_repo_path(out)

    def save(f, screen, cmds, stats):
        if screen is not None and frames is not None:
            save_png(screen, out / ("f%04d.png" % f))

    res = run(bdir, blob, a.ef, frames=set() if a.no_draw else frames, scale=a.scale, max_frames=a.max_frames,
              on_frame=save)
    doc = {k: v for k, v in res.items() if k not in ("stats", "prim_log", "host", "per_frame")}
    doc.update(source=source, plugin_sha256=sha, frames_drawn=sorted(frames) if frames is not None else "all",
               visible_cells=visible_cells(res["stats"]), render_target_cells=visible_cells(res["stats"], gen=True),
               meshes=mesh_summary(res["stats"]), routes=res["stats"].routes)
    out.mkdir(parents=True, exist_ok=True)
    (out / "summary.json").write_text(json.dumps(doc, indent=1, default=list), encoding="utf-8")
    print("ef%03d: %d frames, %d faults, gen texture %s, cache %s -> %s" % (
        a.ef, res["frames"], len(res["faults"]), res["gen_texture_used"], res["texture_cache"], out))
    for cell, v in list(doc["visible_cells"].items())[:40]:
        print("  visible %-16s %7d px  frames %d-%d" % (cell, v["pixels"], v["frames"][0], v["frames"][1]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
