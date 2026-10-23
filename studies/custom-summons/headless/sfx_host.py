r"""HEADLESS -- run the native battle-effect engine outside the game, as an offline oracle.

    py -I sfx_host.py stage                         # copy the install's plugin into the SCRATCH cache
    py -I sfx_host.py run --ef 227                  # one container, from the extracted SCRATCH corpus
    py -I sfx_host.py run --ef 227 --from-install   # ... re-read from the install's resources.assets
    py -I sfx_host.py run --container <path> --ef 227    # an edited / override container
    py -I sfx_host.py census --jobs 6               # every container in the corpus -> SCRATCH census

WHY THIS EXISTS
---------------
``FF9SpecialEffectPlugin.dll`` has no graphics or file imports, 13 exports and ONE host callback
(PLAN.md section 3A). That is a library you can host yourself. Every question TIER R and TIER W
answered by reading the DLL, or by an owner cast with a probe armed, is a question this module can
answer by RUNNING it: which frame a phase starts, where the camera cuts, which VRAM rects are
uploaded, blitted and sampled at which depth, whether a container finishes, asserts or hangs.

The host plays one container per CHILD process (``_child``). The parent classifies the outcome, so a
CRT assert (``ok=False, outcome="assert"``), a native crash or a hang (``"timeout"``, the HIRAISHI
self-loop class) becomes a verdict and not a dead caller. Asserts are routed to stderr BEFORE the
plugin loads -- the CRT's default is a modal dialog on the user's desktop.

WHAT THE STUB HOST IS -- AND IS NOT
-----------------------------------
The callback mirrors ``SFX.BattleCallback`` / ``BattleCallbackWithBtl`` (Memoria ``SFX.cs``) code by
code, including the exact byte layout each code writes through its pointer argument (a wrong width
here corrupts the plugin's stack; the first spike proved it). VRAM is a real 1024x512 halfword
model: LOAD_IMAGE (100) writes it, STORE_IMAGE (101) reads it back into the plugin, MOVE_IMAGE
(102) and non-screen ``DR_MOVE`` prims move it.

Eight actors stand where the stock DEBUG ROOM puts them (``SFX.InitBattleParty`` isDebugMode arm:
``btl_id = 1 << i``, players 0-3) -- at the origin, with one bone per actor at its position. Every
animation is ``motion_frames`` long. THAT is the one calibrated parameter: the plugin waits on the
caster's animation before an effect's program starts, and ``motion_frames = 1`` reproduces the
archived in-game s53 Bahamut cast exactly (every authored H change on its frame, the creature's first
frame on f82 -- ``hx_gates.py`` HX1, with HX2 proving the comparison can fail). Positions matter for
WHERE prims land on screen, not for timing.

NOT modelled: Unity (prims are DATA, not pixels -- rasterising them is ``SFXRender``'s open-source
job), the battle background, the managed ``.seq`` layer (under SFXRework the outer text sequence owns
sounds/fades/damage; this host sees only the native program), real actor rigs, x86 (needs a 32-bit
Python; the x86 plugin build is a different file).

PROVENANCE
----------
The plugin is the USER'S OWN DLL, copied out of their install into the SCRATCH cache and loaded in a
throw-away process -- never committed, never redistributed, never patched. Containers come from the
user's install (``--from-install``, via the kit's ``rescore.read_stock_effect``) or the local SCRATCH
extraction. Everything a run derives from a stock container (per-frame tables, census JSON) is written
under SCRATCH only; ``_refuse_repo_path`` refuses an output path inside the repository.
"""
from __future__ import annotations

import argparse
import ctypes as C
import hashlib
import json
import os
import shutil
import struct
import subprocess
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

_HERE = Path(__file__).resolve().parent
_REPO = _HERE.parents[2]

SCRATCH = Path(os.environ.get("FF9_SUMMON_SCRATCH", r"C:\gd\SCRATCH\summon-format"))
CORPUS = SCRATCH                                     # the FORMAT round's extracted ef###.bytes
BIN_CACHE = SCRATCH / "headless-bin"
OUT_DIR = SCRATCH / "headless"

PLUGIN = "FF9SpecialEffectPlugin.dll"
CRT_DLLS = ("msvcr120.dll", "msvcp120.dll")

def _kit_pinned_builds() -> Dict[str, dict]:
    """The x64 entries of THE ONE pin table, ``ff9mapkit/ff9mapkit/sfxplugin.py`` -- shared with the kit's
    ``[SfxHybrid]`` arm refusal and pinned to the engine's s53/s58/s152 constants by
    ``test_plugin_pins_match_the_engine_patches``, so the host and the drive cannot drift apart. Loaded by
    FILE from this checkout (never an installed kit -- the study-scripts pin trap) and without importing the
    package, because every census child process pays for it. x64 only: this host loads the x64 plugin."""
    import importlib.util
    path = _REPO / "ff9mapkit" / "ff9mapkit" / "sfxplugin.py"
    spec = importlib.util.spec_from_file_location("_ff9mapkit_sfxplugin", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return {sha: pin for sha, pin in mod.PINNED_BUILDS.items() if pin["arch"] == "x64"}


#: Plugin builds whose internal layout is known (summon_rec / summon_active / data_bones / gte_* /
#: view_matrix). The offsets are read ONLY when the staged DLL's sha256 is listed here -- on any other
#: build the slot/camera columns are None and the run says so (the same posture as the s58 drive).
PINNED_BUILDS: Dict[str, dict] = _kit_pinned_builds()

#: A node translation beyond this is recycled-arena garbage, not a pose (s58's SaneMaxTrans).
SANE_MAX_TRANS = 1 << 24

# ============================================================== the plugin's own structs (SFX.cs)
#: ``BTL_DATA_INIT`` -- 32 bytes: 8 bytes of flags, enemy/geo radius + geo height (s32 x3),
#: btl_id (u16) + pad, 4 bytes, weapon offsets (s16 x2).
BTL_DATA_INIT_SIZE = 32
#: ``SFX_INIT_PARAM`` -- pad0[2], FixedCamera1/2, putX/putZ, 8 x BTL_DATA_INIT, camMat[9], camTrans[3],
#: camProj, pad. 300 bytes under the default marshalling; we hand over a zeroed 512.
INIT_PARAM_BUF = 512
INIT_ACTORS_OFF = 8
#: ``S_Eff_Req_Org`` -- 14 x BTL_DATA_REQ (u16 btl_id + pad), trgno, rtrgno, monbone0/1, trgcpos xyz +
#: pad, flgs, arg0 = 72 bytes.
REQ_SIZE = 72
REQ_TRG0_OFF = 8
REQ_TRGNO_OFF = 56

N_ACTORS = 8


def build_init_param(geo_radius: int = 256, geo_height: int = 1024) -> bytearray:
    """The stock debug-room ``SFX_INIT_PARAM``: actor i has btl_id ``1 << i``; 0-3 are players."""
    buf = bytearray(INIT_PARAM_BUF)
    for i in range(N_ACTORS):
        off = INIT_ACTORS_OFF + BTL_DATA_INIT_SIZE * i
        buf[off + 0] = 1 if i < 4 else 0                         # bi_player
        buf[off + 1] = i                                         # bi_slot_no
        struct.pack_into("<iii", buf, off + 8, 0, geo_radius, geo_height)
        struct.pack_into("<H", buf, off + 20, 1 << i)            # btl_id
    return buf


def build_request(exe: int = 1, trg0: int = 16) -> bytearray:
    """``SFX.SetDebug()``: caster = party slot 0 (btl_id 1), one target = enemy 0 (btl_id 16)."""
    buf = bytearray(128)
    struct.pack_into("<H", buf, 0, exe)
    struct.pack_into("<H", buf, REQ_TRG0_OFF, trg0)
    buf[REQ_TRGNO_OFF] = 1
    return buf


# ============================================================== VRAM (1024 x 512 halfwords)
class Vram:
    W, H = 1024, 512

    def __init__(self) -> None:
        self.mem = bytearray(self.W * self.H * 2)

    def _clip(self, x, y, w, h):
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(self.W, x + w), min(self.H, y + h)
        return x0, y0, x1, y1

    def load(self, x: int, y: int, w: int, h: int, src: bytes) -> None:
        """Host->VRAM. ``src`` is ``w*h`` halfwords, row-major."""
        x0, y0, x1, y1 = self._clip(x, y, w, h)
        for row in range(y0, y1):
            s = ((row - y) * w + (x0 - x)) * 2
            d = (row * self.W + x0) * 2
            self.mem[d:d + (x1 - x0) * 2] = src[s:s + (x1 - x0) * 2]

    def store(self, x: int, y: int, w: int, h: int) -> bytes:
        """VRAM->host, ``w*h`` halfwords; outside VRAM reads as zero."""
        out = bytearray(w * h * 2)
        x0, y0, x1, y1 = self._clip(x, y, w, h)
        for row in range(y0, y1):
            d = ((row - y) * w + (x0 - x)) * 2
            s = (row * self.W + x0) * 2
            out[d:d + (x1 - x0) * 2] = self.mem[s:s + (x1 - x0) * 2]
        return bytes(out)

    def move(self, sx: int, sy: int, w: int, h: int, dx: int, dy: int) -> None:
        self.load(dx, dy, w, h, self.store(sx, sy, w, h))


# ============================================================== the stub host (SFXData.BattleCallbackDummy)
class Actor:
    __slots__ = ("btl_id", "player", "pos", "base_pos", "rot", "scale", "anim", "anim_frame",
                 "stop_anim", "disappear", "mesh_count", "target", "slave", "cmd_idle", "flags")

    def __init__(self, btl_id: int, player: bool) -> None:
        self.btl_id = btl_id
        self.player = player
        self.pos = [0, 0, 0]          # PSX units; y is down
        self.base_pos = [0, 0, 0]
        self.rot = [0, 0, 0]          # PSX angle units (4096 = 360 degrees)
        self.scale = [4096, 4096, 4096]
        self.anim = 0
        self.anim_frame = 0
        self.stop_anim = 0
        self.disappear = 0
        self.mesh_count = 1
        self.target = 1
        self.slave = 0
        self.cmd_idle = 0
        self.flags = 0


def _s16(v: int) -> int:
    return max(-32768, min(32767, int(v)))


class Host:
    """The plugin's view of the battle. ``callback`` is what ``SFX_InitSystem`` is handed.

    Two answer sets, both transcribed from Memoria's open source:

    * ``mode="rework"`` (DEFAULT -- what the live game runs): ``SFXData.BattleCallbackDummy`` with
      ``BattleCallbackDummyLoadImages = true``, the callback ``SFXDataMesh.Runtime.Begin`` installs
      for every SFXRework cast (SFXRework is forced at Speed >= 3, and on by default). VRAM traffic
      is live; sounds, fades, damage points and every SET call are swallowed; the animation queries
      answer a literal 1 (frame count AND current frame); Stop Animation echoes its argument.
    * ``mode="legacy"``: ``SFX.BattleCallback`` (SFXRework = 0) -- stateful positions, angles and
      animation frames (``motion_frames`` long), the previous stop-animation value returned.

    Either way every code is counted, and the ones a study cares about (sounds, effect/figure points,
    intensity, VRAM traffic) are logged per frame even where the live game swallows them -- the
    log says what the PROGRAM asked for, not what Unity did with it.
    """

    def __init__(self, mode: str = "rework", motion_frames: int = 1, alive_players: int = 4) -> None:
        if mode not in ("rework", "legacy"):
            raise ValueError("mode must be 'rework' or 'legacy', not %r" % mode)
        self.mode = mode
        self.motion_frames = max(1, int(motion_frames))
        self.alive_players = alive_players
        self.actors = {1 << i: Actor(1 << i, i < 4) for i in range(N_ACTORS)}
        self.vram = Vram()
        self.frame = -1                      # -1 = during SFX_Play
        self.codes: Counter = Counter()
        self.events: List[Tuple[int, str, tuple]] = []    # (frame, kind, args)
        self.vram_ops: List[Tuple[int, str, tuple]] = []
        self.bg_intensity = 128
        self.errors: List[str] = []

    # ---- small helpers
    def _log(self, kind: str, *args) -> None:
        self.events.append((self.frame, kind, args))

    @staticmethod
    def _put(p: int, data: bytes) -> None:
        if p:
            C.memmove(p, data, len(data))

    @staticmethod
    def _get(p: int, n: int) -> bytes:
        return C.string_at(p, n) if p else b"\0" * n

    def tick(self) -> None:
        """Legacy mode: advance every looping actor animation by one frame (the battle animator)."""
        if self.mode == "legacy":
            for a in self.actors.values():
                a.anim_frame = (a.anim_frame + 1) % self.motion_frames

    # ---- the callback
    def callback(self, full: int, a0: int, a1: int, a2: int, a3: int, p) -> int:
        try:
            return self._dispatch(full, a0, a1, a2, a3, int(p or 0))
        except Exception as e:                     # never unwind into native code
            self.errors.append("code %d: %r" % ((full >> 24) & 0xFF, e))
            return 0

    def _dispatch(self, full: int, a0: int, a1: int, a2: int, a3: int, p: int) -> int:
        code = (full >> 24) & 0xFF
        self.codes[code] += 1
        rework = self.mode == "rework"
        if code == 100:                            # LOAD_IMAGE [x,y,w,h] <- p
            if a2 > 0 and a3 > 0:
                self.vram.load(a0, a1, a2, a3, self._get(p, a2 * a3 * 2))
            self.vram_ops.append((self.frame, "load", (a0, a1, a2, a3)))
            return 0
        if code == 32:                             # play/stop sound: a0 mode, a1 id (rework: swallowed)
            self._log("sound", a0, a1, a2)
            return 0
        if code == 101:                            # STORE_IMAGE [x,y,w,h] -> p
            if a2 > 0 and a3 > 0:
                self._put(p, self.vram.store(a0, a1, a2, a3))
            self.vram_ops.append((self.frame, "store", (a0, a1, a2, a3)))
            return 0
        if code == 102:                            # MOVE_IMAGE p=[sx,sy,w,h] -> (a0,a1)
            sx, sy, w, h = struct.unpack("<4h", self._get(p, 8))
            if w > 0 and h > 0:
                self.vram.move(sx, sy, w, h, a0, a1)
            self.vram_ops.append((self.frame, "move", (sx, sy, w, h, a0, a1)))
            return 0
        if code == 117:
            return self.bg_intensity
        if code == 118:                            # rework: swallowed (the .seq owns fades)
            if not rework:
                self.bg_intensity = a0
            self._log("bg_intensity", a0, a1)
            return 0
        if code == 113:
            self._log("title", a0, a1)
            return 0
        if code == 121:                            # member_flag: party btl_ids still in battle
            return 0x0F
        if code == 123:
            return self.alive_players
        if code in (110, 111, 112, 114, 115, 116, 119, 120, 122, 124, 125):
            return 0
        return self._actor_code(code, full & 0xFF, a0, a1, a2, a3, p)

    def _actor_code(self, code, btlid, a0, a1, a2, a3, p) -> int:
        act = self.actors.get(btlid)
        if act is None:                            # no such unit: the engine's own fallback
            return 1 if code == 9 else 0
        rework = self.mode == "rework"
        if code == 23:
            self._log("effect_point", btlid, a0, a1)
            return 0
        if code == 24:
            self._log("figure_point", btlid, a0, a1)
            return 0
        if code == 25:
            self._log("show_mesh", btlid, a0, a1)
            return 0
        if code in (29, 30, 31):
            self._log("sound_actor", code, btlid, a0, a1)
            return 0
        if code == 12:
            self._log("motion", btlid, a0)
        if rework and code in (2, 4, 6, 11, 12, 16, 17, 18, 19, 20, 21, 22, 27, 28, 33):
            return 0                               # BattleCallbackDummy: every SET is a no-op
        if code == 1:                              # Get Position
            src = act.pos if a0 in (0, 2) else act.base_pos
            if a0 in (0, 1):
                self._put(p, struct.pack("<3h", *map(_s16, src)))
            elif a0 in (2, 3):                     # 2D: x and z only
                self._put(p, struct.pack("<h", _s16(src[0])))
                self._put(p + 4 if p else 0, struct.pack("<h", _s16(src[2])))
            return 0
        if code == 2:                              # Set Position (legacy)
            act.pos = list(struct.unpack("<3h", self._get(p, 6)))
            return 0
        if code == 3:                              # Get Angles
            r = [0, 0, 0] if a0 == 0 else act.rot
            if a0 == 3:
                self._put(p, struct.pack("<h", _s16(r[0])))
                self._put(p + 4 if p else 0, struct.pack("<h", _s16(r[2])))
            else:
                self._put(p, struct.pack("<3h", *map(_s16, r)))
            return 0
        if code == 4:                              # Set Angles (legacy)
            if a0 == 2:
                act.rot = list(struct.unpack("<3h", self._get(p, 6)))
            return 0
        if code == 5:                              # Get Size -- three s32, fp12
            self._put(p, struct.pack("<3i", *act.scale))
            return 0
        if code == 7:
            return act.flags
        if code == 9:                              # Current animation's frame count
            return 1 if rework else self.motion_frames
        if code == 10:                             # Current animation's current frame
            return 1 if rework else act.anim_frame
        if code == 11:                             # Set frame, clamped to the last (legacy)
            act.anim_frame = min(max(0, a0), self.motion_frames - 1)
            return 0
        if code == 12:                             # Set animation (legacy)
            act.anim = a0
            act.anim_frame = 0
            return 0
        if code == 13:                             # Stop animation
            if rework:
                return a0
            old, act.stop_anim = act.stop_anim, a0 & 0xFF
            return old
        if code == 14:                             # Get Bone Stance (a0 = mode, a1 = bone)
            x, y, z = act.pos
            if a0 == 0:
                self._put(p, struct.pack("<3h", _s16(x), _s16(y), _s16(z)))
            elif a0 == 1:
                return int(y)                      # -(Unity m13) == the PSX y of the bone
            elif a0 == 2:                          # PSXMAT r[9] s16, pad s16, t[3] s32 (identity, managed signs)
                self._put(p, struct.pack("<9hh3i", -4096, 0, 0, 0, 4096, 0, 0, 0, 4096, 0, x, y, z))
            return 0
        if code == 15:
            return 1 if rework else act.target
        if code == 17:
            return 1 if act.disappear else 0
        if code == 18:
            act.disappear = a0
            return 0
        if code == 21:
            return act.cmd_idle
        if code == 22:
            return act.slave
        if code == 26:
            return act.mesh_count
        return 0                                   # 6, 8, 16, 19, 20, 27, 28, 33, ... : nothing to model


# ============================================================== primitive decoding (PSX libgpu)
POLY_FT3, POLY_FT4, POLY_GT3, POLY_GT4 = 0x24, 0x2C, 0x34, 0x3C
SPRT, SPRT_8, SPRT_16 = 0x64, 0x74, 0x7C
DR_TPAGE, DR_MOVE = 0xE1, 0xE7
#: (uv word indices, clut word, tpage word, xy word indices) inside the body that follows the tag
POLY_UV = {
    POLY_FT3: ((2, 4, 6), 2, 4, (1, 3, 5)),
    POLY_FT4: ((2, 4, 6, 8), 2, 4, (1, 3, 5, 7)),
    POLY_GT3: ((2, 5, 8), 2, 5, (1, 4, 7)),
    POLY_GT4: ((2, 5, 8, 11), 2, 5, (1, 4, 7, 10)),
}
#: The PSX framebuffer the plugin projects into (OFX/OFY = 160/120). A prim whose screen box misses it
#: is emitted but cannot be seen -- widescreen only adds columns the stock framing never authored for.
SCREEN_W, SCREEN_H = 320, 240
BPP_NAMES = {0: 4, 1: 8, 2: 15, 3: 15}


def tpage_fields(tp: int) -> Tuple[int, int, int, int]:
    """tpage word -> (page_x halfwords, page_y lines, abr, bpp)."""
    return (tp & 0xF) * 64, ((tp >> 4) & 1) * 256, (tp >> 5) & 3, BPP_NAMES[(tp >> 7) & 3]


def clut_fields(cw: int) -> Tuple[int, int]:
    return (cw & 0x3F) * 16, (cw >> 6) & 0x1FF


def sampled_rect(tp: int, umin: int, umax: int, vmin: int, vmax: int) -> Tuple[int, int, int, int, int]:
    """The VRAM halfword rect ``(x0, y0, x1, y1)`` a UV box samples under tpage ``tp``, plus its bpp.

    4bpp packs 4 texels per halfword, 8bpp 2, 15bpp 1 -- the page-span rule (G1): an 8bpp page covers
    two 64-halfword columns, a 15bpp one four."""
    px, py, _, bpp = tpage_fields(tp)
    div = {4: 4, 8: 2, 15: 1}[bpp]
    return px + umin // div, py + vmin, px + umax // div, py + vmax, bpp


def cells_of(rect: Tuple[int, int, int, int]) -> List[Tuple[int, int]]:
    """The kit's 64x128 VRAM cells a halfword rect touches (``cell.sN.x<X>_y<Y>`` naming)."""
    x0, y0, x1, y1 = rect
    x0, x1 = max(0, x0), min(1023, x1)
    y0, y1 = max(0, y0), min(511, y1)
    return [(cx, cy) for cx in range(x0 // 64 * 64, x1 + 1, 64)
            for cy in range(y0 // 128 * 128, y1 + 1, 128)]


def _on_screen(xs, ys) -> bool:
    return max(xs) >= 0 and min(xs) < SCREEN_W and max(ys) >= 0 and min(ys) < SCREEN_H


def _xy(word: int) -> Tuple[int, int]:
    return C.c_int16(word & 0xFFFF).value, C.c_int16(word >> 16).value


class PrimStats:
    """Everything a run keeps from the prim stream: counts, a stream hash, DR_MOVEs, sampled cells.

    "Sampled" means a textured prim the plugin EMITTED reads that VRAM cell; ``on_screen`` counts the
    ones whose screen box meets the PSX framebuffer. Neither is a claim that Unity drew a visible
    pixel: blending, transparent texels and the managed renderer sit between the two."""

    def __init__(self) -> None:
        self.codes: Counter = Counter()
        self.sha = hashlib.sha256()
        self.dr_moves: Dict[tuple, List[int]] = defaultdict(list)     # (src,size,dst) -> frames
        self.samples: Counter = Counter()          # (tpage, clut, umin, umax, vmin, vmax, on_screen) -> prims
        self.sample_frames: Dict[tuple, List[int]] = {}
        self.tpage_state = 0
        self.total = 0

    def add(self, frame: int, code: int, body: bytes, otz: int) -> None:
        self.total += 1
        self.codes[code] += 1
        self.sha.update(body)
        self.sha.update(struct.pack("<i", otz))
        base = code & 0xFC
        if base in POLY_UV and code & 0x04:        # bit 2 set = textured (FT/GT)
            uvw, ci, ti, xyw = POLY_UV[base]
            words = struct.unpack_from("<%dI" % (len(body) // 4), body)
            if max(uvw) >= len(words):
                return
            us = [words[i] & 0xFF for i in uvw]
            vs = [(words[i] >> 8) & 0xFF for i in uvw]
            pts = [_xy(words[i]) for i in xyw]
            on = _on_screen([x for x, _ in pts], [y for _, y in pts])
            self._sample(frame, words[ti] >> 16, words[ci] >> 16, us, vs, on)
        elif base in (SPRT, SPRT_8, SPRT_16) and code & 0x04:
            words = struct.unpack_from("<%dI" % (len(body) // 4), body)
            if len(words) < 3:
                return
            u, v, cw = words[2] & 0xFF, (words[2] >> 8) & 0xFF, words[2] >> 16
            if base == SPRT and len(words) >= 4:
                w, h = words[3] & 0xFFFF, words[3] >> 16
            else:
                w = h = 8 if base == SPRT_8 else 16
            x, y = _xy(words[1])
            self._sample(frame, self.tpage_state, cw, [u, min(255, u + max(0, w - 1))],
                         [v, min(255, v + max(0, h - 1))], _on_screen([x, x + w], [y, y + h]))
        elif code == DR_TPAGE and len(body) >= 4:
            self.tpage_state = struct.unpack_from("<I", body)[0] & 0x1FF
        elif code == DR_MOVE and len(body) >= 16:
            _, w1, w2, w3 = struct.unpack_from("<4I", body)
            key = ((w1 >> 16, w1 & 0xFFFF), (w2 >> 16, w2 & 0xFFFF), (w3 >> 16, w3 & 0xFFFF))
            self.dr_moves[key].append(frame)

    def _sample(self, frame, tp, cw, us, vs, on: bool = True) -> None:
        key = (tp & 0x1FF, cw, min(us), max(us), min(vs), max(vs), bool(on))
        self.samples[key] += 1
        fr = self.sample_frames.get(key)
        if fr is None:
            self.sample_frames[key] = [frame, frame]
        else:
            fr[1] = frame

    def sampled_cells(self) -> Dict[str, dict]:
        """``"x704_y384@8"`` -> {prims, on_screen, cluts, frames} over every textured prim sampling it."""
        out: Dict[str, dict] = {}
        for key, n in self.samples.items():
            tp, cw, umin, umax, vmin, vmax, on = key
            x0, y0, x1, y1, bpp = sampled_rect(tp, umin, umax, vmin, vmax)
            for cx, cy in cells_of((x0, y0, x1, y1)):
                name = "x%d_y%d@%d" % (cx, cy, bpp)
                d = out.setdefault(name, {"prims": 0, "on_screen": 0, "cluts": set(), "frames": [1 << 30, -1]})
                d["prims"] += n
                d["on_screen"] += n if on else 0
                d["cluts"].add("%d,%d" % clut_fields(cw))
                f0, f1 = self.sample_frames[key]
                d["frames"] = [min(d["frames"][0], f0), max(d["frames"][1], f1)]
        for d in out.values():
            d["cluts"] = sorted(d["cluts"])
        return out

    def dr_move_cells(self) -> Dict[str, dict]:
        """Blit destinations as cells: ``"x704_y384"`` -> {blits, from: [source cells], frames}."""
        out: Dict[str, dict] = {}
        for (src, size, dst), frames in self.dr_moves.items():
            if src[0] < 320 and src[1] < 240:      # a screen grab (SFXScreenShot), not a VRAM move
                continue
            for cell in cells_of((dst[0], dst[1], dst[0] + size[0] - 1, dst[1] + size[1] - 1)):
                d = out.setdefault("x%d_y%d" % cell, {"blits": 0, "from": set(), "frames": [1 << 30, -1]})
                d["blits"] += len(frames)
                for sc in cells_of((src[0], src[1], src[0] + size[0] - 1, src[1] + size[1] - 1)):
                    d["from"].add("x%d_y%d" % sc)
                d["frames"] = [min(d["frames"][0], frames[0]), max(d["frames"][1], frames[-1])]
        for d in out.values():
            d["from"] = sorted(d["from"])
        return out


# ============================================================== staging the user's plugin
def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _import_kit():
    """The kit, from THIS checkout (never the main repo's -- the study-scripts pin trap)."""
    kit = str(_REPO / "ff9mapkit")
    if kit not in sys.path:
        sys.path.insert(0, kit)
    import ff9mapkit                                            # noqa: F401
    here = Path(ff9mapkit.__file__).resolve()
    if _REPO not in here.parents:
        raise RuntimeError("imported ff9mapkit from %s, not this checkout %s" % (here, _REPO))
    return ff9mapkit


def plugin_dir_in_install(game) -> Path:
    for cand in (Path(game) / "x64" / "FF9_Data" / "Plugins", Path(game) / "FF9_Data" / "Plugins"):
        if (cand / PLUGIN).is_file():
            return cand
    raise FileNotFoundError("no %s under %s (x64/FF9_Data/Plugins or FF9_Data/Plugins)" % (PLUGIN, game))


def stage_plugin(game=None, cache: Path = BIN_CACHE) -> Tuple[Path, str]:
    """Copy the install's x64 plugin + its CRTs into ``<cache>/<sha12>/``; return (dir, sha256).

    Idempotent: an already-staged build of the same sha is reused."""
    if game is None:
        _import_kit()
        from ff9mapkit import config                           # noqa: E402
        game = config.find_game_path(None)
    src = plugin_dir_in_install(game)
    sha = _sha256(src / PLUGIN)
    dst = Path(cache) / sha[:12]
    if not (dst / PLUGIN).is_file() or _sha256(dst / PLUGIN) != sha:
        dst.mkdir(parents=True, exist_ok=True)
        for name in (PLUGIN,) + CRT_DLLS:
            if (src / name).is_file():
                shutil.copy2(src / name, dst / name)
            elif (src.parent.parent / name).is_file():         # x64/msvcr120.dll layout
                shutil.copy2(src.parent.parent / name, dst / name)
    return dst, sha


def staged_bins(cache: Path = BIN_CACHE) -> List[Tuple[Path, str]]:
    out = []
    if Path(cache).is_dir():
        for d in sorted(Path(cache).iterdir()):
            if (d / PLUGIN).is_file():
                out.append((d, _sha256(d / PLUGIN)))
    return out


def resolve_bin(bin_dir: Optional[str], game=None) -> Tuple[Path, str]:
    if bin_dir:
        d = Path(bin_dir)
        return d, _sha256(d / PLUGIN)
    have = staged_bins()
    if len(have) == 1:
        return have[0]
    return stage_plugin(game)


def _refuse_repo_path(path: Path) -> Path:
    p = Path(path).resolve()
    if p == _REPO or _REPO in p.parents:
        raise SystemExit("refusing to write %s: it is inside the repository, and a headless run's output "
                         "is derived from stock containers -- write under SCRATCH (%s)" % (p, SCRATCH))
    return p


# ============================================================== the child: one container, one process
def _install_no_dialog(bin_dir: Path) -> None:
    """Route the plugin's CRT asserts/aborts to stderr. MUST run before the plugin loads."""
    os.add_dll_directory(str(bin_dir))
    C.windll.kernel32.SetErrorMode(0x0001 | 0x0002 | 0x8000)
    crt = C.CDLL(str(bin_dir / "msvcr120.dll"))
    crt._set_error_mode(1)                         # _OUT_TO_STDERR
    crt._set_abort_behavior(0, 0x1 | 0x2)          # no abort message box, no WER report


def run_in_process(bin_dir: Path, blob: bytes, effnum: int, *, mode: str = "rework", motion_frames: int = 1,
                   max_frames: int = 8000, pin: Optional[dict] = None,
                   frames_csv: Optional[Path] = None) -> dict:
    """Load the plugin into THIS process and play one container. Use ``run_effect`` from outside."""
    _install_no_dialog(bin_dir)
    dll = C.CDLL(str(bin_dir / PLUGIN))
    host = Host(mode=mode, motion_frames=motion_frames)
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
    param = build_init_param()
    pbuf = (C.c_ubyte * len(param)).from_buffer(param)
    dll.SFX_InitBattle(C.addressof(pbuf))
    req = build_request()
    rbuf = (C.c_ubyte * len(req)).from_buffer(req)
    bbuf = (C.c_ubyte * len(blob)).from_buffer_copy(blob)
    dll.SFX_Play(effnum, C.addressof(bbuf), len(blob), C.addressof(rbuf))

    base = dll._handle
    prims = PrimStats()
    rows = []
    frame = C.c_int32(0)
    ended = None
    for n in range(max_frames):
        host.frame = n + 1                         # every logged frame is the plugin's frameIndex
        running = dll.SFX_Update(C.byref(frame))
        dll.SFX_LateUpdate()
        count = 0
        if dll.SFX_BeginRender():
            while True:
                otz = C.c_int32(0)
                ptr = dll.SFX_GetPrim(C.byref(otz))
                if not ptr:
                    break
                ln = C.c_ubyte.from_address(ptr + 3).value
                code = C.c_ubyte.from_address(ptr + 7).value
                body = C.string_at(ptr + 4, ln * 4)
                prims.add(frame.value, code, body, otz.value)
                if code == DR_MOVE and len(body) >= 16:
                    # SFXRender.DR_MOVE -> SFXMoveImage -> PSXTextureMgr.MoveImage writes the same
                    # originalVram a later STORE_IMAGE reads; a screen-area source is a screenshot.
                    _, w1, w2, w3 = struct.unpack_from("<4I", body)
                    rx, ry = w1 >> 16, C.c_int16(w1 & 0xFFFF).value
                    if not (rx < 320 and ry < 240):
                        host.vram.move(rx, ry, w2 >> 16, w2 & 0xFFFF, w3 >> 16, w3 & 0xFFFF)
                count += 1
        # ``frame`` is the plugin's own frameIndex (== n + 1 while running) -- the number every in-game
        # probe logs, so every comparison keys on it. The pinned columns are sampled HERE, after the
        # prim walk and BEFORE SFX_UpdateCamera, which is where the s53 probe reads them in game
        # (during SFXRender): the view matrix is the plugin tick's, H is the previous install's.
        row = {"n": n, "frame": frame.value, "prims": count}
        if pin:
            rec = base + pin["summon_rec"]
            active = C.c_ubyte.from_address(rec + pin["summon_active"]).value
            sdata = C.c_void_p.from_address(rec).value
            bones = C.c_void_p.from_address(sdata + pin["data_bones"]).value if sdata else None
            t0 = struct.unpack("<3i", C.string_at(bones + 0x14, 12)) if bones else None
            vm = base + pin["view_matrix"]
            row.update(active=active, bones=bool(bones), t0=t0,
                       M=struct.unpack("<9h", C.string_at(vm, 18)) + struct.unpack("<3i", C.string_at(vm + 0x14, 12)),
                       H=C.c_uint16.from_address(base + pin["gte_h"]).value,
                       OFX=C.c_int16.from_address(base + pin["gte_ofx"]).value,
                       OFY=C.c_int16.from_address(base + pin["gte_ofy"]).value)
        row["cam"] = bool(dll.SFX_UpdateCamera(0))
        rows.append(row)
        host.tick()
        if not running:
            ended = n
            break

    if frames_csv:
        _write_frames_csv(frames_csv, rows)
    return summarize(effnum, blob, rows, prims, host, ended, pin is not None, motion_frames)


def _write_frames_csv(path: Path, rows: List[dict]) -> None:
    path = _refuse_repo_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    keys = list(rows[0].keys()) if rows else []
    with open(path, "w", encoding="utf-8") as f:
        f.write(",".join(keys) + "\n")
        for r in rows:
            f.write(",".join("" if r.get(k) is None else str(r[k]).replace(",", " ") for k in keys) + "\n")


def h_changes(rows: Sequence[dict]) -> List[Tuple[int, int]]:
    """``(frameIndex, H)`` wherever the projection distance changes, after the first frame."""
    out = []
    for prev, cur in zip(rows, rows[1:]):
        if cur.get("H") is not None and cur["H"] != prev.get("H"):
            out.append((cur["frame"], cur["H"]))
    return out


def creature_window(rows: Sequence[dict]) -> Optional[Tuple[int, int, int]]:
    """``(first, last, count)`` frameIndex of frames with an active summon slot, bones and a sane node 0."""
    w = [r["frame"] for r in rows if r.get("active") and r.get("bones") and r.get("t0")
         and max(abs(v) for v in r["t0"]) < SANE_MAX_TRANS]
    return (w[0], w[-1], len(w)) if w else None


def summarize(effnum, blob, rows, prims: PrimStats, host: Host, ended, pinned, motion_frames) -> dict:
    nz = [r["frame"] for r in rows if r["prims"]]
    return {
        "effect": effnum,
        "container_sha256": hashlib.sha256(blob).hexdigest(),
        "host_mode": host.mode,
        "motion_frames": motion_frames,
        "frames": len(rows),
        "ended_at": ended,
        "native_frame_index": rows[-1]["frame"] if rows else None,
        "prims_total": prims.total,
        "prim_frames": [nz[0], nz[-1], len(nz)] if nz else None,
        "max_prims_per_frame": max((r["prims"] for r in rows), default=0),
        "camera_frames": sum(1 for r in rows if r["cam"]),
        "stream_sha256": prims.sha.hexdigest(),
        "prim_codes": {"0x%02X" % k: v for k, v in sorted(prims.codes.items())},
        "pinned_layout": pinned,
        "h_changes": h_changes(rows) if pinned else None,
        "creature_window": creature_window(rows) if pinned else None,
        "sampled_cells": prims.sampled_cells(),
        "dr_move_dst_cells": prims.dr_move_cells(),
        "callbacks": {str(k): v for k, v in sorted(host.codes.items())},
        "vram_ops": Counter(k for _, k, _ in host.vram_ops),
        "vram_uploads": [list(a) for f, k, a in host.vram_ops if k == "load"],
        "events": [[f, k, list(a)] for f, k, a in host.events if k != "motion"],
        "motions": [[f, list(a)] for f, k, a in host.events if k == "motion"],
        "host_errors": host.errors,
    }


# ============================================================== the parent: classify the child
RESULT_TAG = "HXRESULT "


def classify(rc: Optional[int], stderr: str, timed_out: bool, have_result: bool) -> str:
    """ok / assert / timeout / crash / error -- the verdict a census row carries."""
    if timed_out:
        return "timeout"
    if rc == 0 and have_result:
        return "ok"
    if "Assertion failed" in (stderr or ""):
        return "assert"
    if rc not in (0, 1):
        return "crash"
    return "error"


def load_container(effnum: int, container: Optional[str], from_install: bool, game=None,
                   corpus: Path = CORPUS) -> Tuple[bytes, str, Optional[Path]]:
    """``(bytes, source description, on-disk path or None)`` -- a path is handed to the child as-is."""
    if container:
        return Path(container).read_bytes(), str(container), Path(container)
    if from_install:
        _import_kit()
        from ff9mapkit.summons import rescore                  # noqa: E402
        blob, src = rescore.read_stock_effect(effnum, game)
        return blob, src, None
    path = Path(corpus) / ("ef%03d.bytes" % effnum)
    return path.read_bytes(), str(path), path


def run_effect(effnum: int, *, container: Optional[str] = None, from_install: bool = False,
               bin_dir: Optional[str] = None, game=None, mode: str = "rework", motion_frames: int = 1,
               max_frames: int = 8000, timeout: float = 120.0,
               frames_csv: Optional[str] = None) -> dict:
    """Play one container in a child process and return its summary plus an ``outcome`` verdict."""
    blob, source, blob_path = load_container(effnum, container, from_install, game)
    bdir, sha = resolve_bin(bin_dir, game)
    if blob_path is None:                          # read from the install: hand the child a SCRATCH copy
        tmp = _refuse_repo_path(OUT_DIR / "_in")
        tmp.mkdir(parents=True, exist_ok=True)
        blob_path = tmp / ("ef%03d_%s.bytes" % (effnum, hashlib.sha256(blob).hexdigest()[:12]))
        if not blob_path.exists():
            blob_path.write_bytes(blob)
    args = {"bin": str(bdir), "blob": str(blob_path), "effnum": effnum, "mode": mode, "motion_frames": motion_frames,
            "max_frames": max_frames, "sha": sha,
            "frames_csv": str(_refuse_repo_path(Path(frames_csv))) if frames_csv else None}
    t0 = time.time()
    try:
        cp = subprocess.run([sys.executable, "-I", str(Path(__file__).resolve()), "_child", json.dumps(args)],
                            capture_output=True, text=True, timeout=timeout)
        rc, out, err, timed_out = cp.returncode, cp.stdout, cp.stderr, False
    except subprocess.TimeoutExpired as e:
        rc, timed_out = None, True
        out = e.stdout.decode() if isinstance(e.stdout, bytes) else (e.stdout or "")
        err = e.stderr.decode() if isinstance(e.stderr, bytes) else (e.stderr or "")
    result = None
    for line in out.splitlines():
        if line.startswith(RESULT_TAG):
            result = json.loads(line[len(RESULT_TAG):])
    res = result or {"effect": effnum, "container_sha256": hashlib.sha256(blob).hexdigest()}
    res.update(outcome=classify(rc, err, timed_out, result is not None), returncode=rc,
               seconds=round(time.time() - t0, 2), source=source, plugin_sha256=sha,
               stderr_tail=[ln for ln in (err or "").splitlines() if ln.strip()][-3:])
    return res


def _child_main(argjson: str) -> int:
    a = json.loads(argjson)
    pin = PINNED_BUILDS.get(a["sha"])
    res = run_in_process(Path(a["bin"]), Path(a["blob"]).read_bytes(), a["effnum"],
                         mode=a.get("mode", "rework"), motion_frames=a["motion_frames"],
                         max_frames=a["max_frames"], pin=pin,
                         frames_csv=Path(a["frames_csv"]) if a.get("frames_csv") else None)
    print(RESULT_TAG + json.dumps(res, default=list), flush=True)
    return 0


# ============================================================== census
def corpus_ids(corpus: Path = CORPUS) -> List[int]:
    out = []
    for p in sorted(Path(corpus).glob("ef[0-9][0-9][0-9].bytes")):
        out.append(int(p.stem[2:]))
    return out


def census(ids: Sequence[int], *, jobs: int = 4, timeout: float = 120.0, mode: str = "rework", motion_frames: int = 1,
           out_dir: Path = OUT_DIR, bin_dir: Optional[str] = None, progress=print) -> dict:
    out_dir = _refuse_repo_path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    bdir, sha = resolve_bin(bin_dir)
    rows: Dict[int, dict] = {}

    def one(e):
        return e, run_effect(e, bin_dir=str(bdir), mode=mode, motion_frames=motion_frames, timeout=timeout)

    with ThreadPoolExecutor(max_workers=max(1, jobs)) as ex:
        for i, (e, r) in enumerate(ex.map(one, ids), 1):
            rows[e] = r
            if progress and (i % 25 == 0 or r["outcome"] != "ok"):
                progress("  [%3d/%d] ef%03d %s" % (i, len(ids), e, r["outcome"]))
    outcomes = Counter(r["outcome"] for r in rows.values())
    doc = {"plugin_sha256": sha, "host_mode": mode, "motion_frames": motion_frames, "timeout_s": timeout,
           "containers": len(rows), "outcomes": dict(outcomes),
           "rows": {"ef%03d" % e: rows[e] for e in sorted(rows)}}
    with open(out_dir / "census.json", "w", encoding="utf-8") as f:
        json.dump(doc, f, default=list)
    with open(out_dir / "census.tsv", "w", encoding="utf-8") as f:
        f.write("effect\toutcome\tframes\tended_at\tprims\tcreature_first\tcreature_last\t"
                "sampled_cells\tblit_dst_cells\tseconds\n")
        for e in sorted(rows):
            r = rows[e]
            cw = r.get("creature_window") or (None, None, None)
            f.write("ef%03d\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n" % (
                e, r["outcome"], r.get("frames"), r.get("ended_at"), r.get("prims_total"),
                cw[0], cw[1], len(r.get("sampled_cells") or {}), len(r.get("dr_move_dst_cells") or {}),
                r.get("seconds")))
    return doc


# ============================================================== CLI
def _print_summary(r: dict) -> None:
    print("ef%03d  outcome=%s  frames=%s ended_at=%s  prims=%s  %.1fs" % (
        r["effect"], r["outcome"], r.get("frames"), r.get("ended_at"), r.get("prims_total"),
        r.get("seconds", 0)))
    if r["outcome"] != "ok":
        for ln in r.get("stderr_tail") or []:
            print("  stderr:", ln)
        return
    print("  container sha %s  stream sha %s" % (r["container_sha256"][:16], r["stream_sha256"][:16]))
    if r.get("pinned_layout"):
        print("  H changes:", r["h_changes"])
        print("  creature window (first, last, frames):", r["creature_window"])
    else:
        print("  (unpinned plugin build: no slot / camera columns)")
    cells = r.get("sampled_cells") or {}
    print("  sampled cells: %d  blit destinations: %d  sounds: %d" % (
        len(cells), len(r.get("dr_move_dst_cells") or {}),
        sum(1 for e in r.get("events") or [] if e[1] == "sound")))


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ["_child"]:
        return _child_main(argv[1])
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sp = sub.add_parser("stage", help="copy the install's plugin into the SCRATCH cache")
    sp.add_argument("--game")
    rp = sub.add_parser("run", help="play one container headless")
    rp.add_argument("--ef", type=int, required=True)
    rp.add_argument("--container")
    rp.add_argument("--from-install", action="store_true")
    rp.add_argument("--game")
    rp.add_argument("--bin")
    rp.add_argument("--mode", choices=("rework", "legacy"), default="rework")
    rp.add_argument("--motion-frames", type=int, default=1, help="legacy mode only")
    rp.add_argument("--max-frames", type=int, default=8000)
    rp.add_argument("--timeout", type=float, default=120.0)
    rp.add_argument("--frames-csv", help="per-frame table (SCRATCH only)")
    rp.add_argument("--json", help="write the full summary JSON here (SCRATCH only)")
    cp = sub.add_parser("census", help="play every corpus container")
    cp.add_argument("--jobs", type=int, default=4)
    cp.add_argument("--timeout", type=float, default=120.0)
    cp.add_argument("--mode", choices=("rework", "legacy"), default="rework")
    cp.add_argument("--motion-frames", type=int, default=1, help="legacy mode only")
    cp.add_argument("--only", help="comma-separated effect ids")
    cp.add_argument("--out", default=str(OUT_DIR))
    cp.add_argument("--bin")
    a = ap.parse_args(argv)
    if a.cmd == "stage":
        d, sha = stage_plugin(a.game)
        print("staged %s  sha256 %s  layout %s" % (d, sha, "PINNED" if sha in PINNED_BUILDS else "UNPINNED"))
        return 0
    if a.cmd == "run":
        r = run_effect(a.ef, container=a.container, from_install=a.from_install, bin_dir=a.bin,
                       game=a.game, mode=a.mode, motion_frames=a.motion_frames, max_frames=a.max_frames,
                       timeout=a.timeout, frames_csv=a.frames_csv)
        _print_summary(r)
        if a.json:
            p = _refuse_repo_path(Path(a.json))
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(r, default=list), encoding="utf-8")
        return 0 if r["outcome"] == "ok" else 1
    if a.cmd == "census":
        ids = [int(x) for x in a.only.split(",")] if a.only else corpus_ids()
        doc = census(ids, jobs=a.jobs, timeout=a.timeout, mode=a.mode, motion_frames=a.motion_frames,
                     out_dir=Path(a.out), bin_dir=a.bin)
        print("census: %d containers  %s  -> %s" % (doc["containers"], doc["outcomes"], a.out))
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
