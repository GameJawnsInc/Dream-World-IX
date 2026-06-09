"""Tune a forked battle's gameplay (the BTL_SCENE ``dbfile0000.raw16``) from a battle.toml ``[scene]``.

A tier-c mint forks a donor battle's raw16 verbatim; this module SURGICALLY patches it with author
overrides -- enemy positions, stats, rewards, and the camera pose -- WITHOUT changing enemy TYPES (so the
forked raw17 attack sequences + the loaded enemy GEO/models stay valid). Only the edited fields change;
every other byte is verbatim, so we never risk mis-packing the 116-byte monster struct.

Layout (from Memoria ``BTL_SCENE.ReadBattleScene``):
  header 8B: Ver(1) PatCount(1) TypCount(1) AtkCount(1) Flags(2) pad(2)
  pattern i @ 8 + 56*i (56B): Rate(1) MonsterCount(1) Camera(1) Pad0(1) AP(u32) then 4x SB2_PUT(12B)
    SB2_PUT j @ +8 + 12*j: TypeNo(1) Flags(1) Pease(1) Pad(1) Xpos(i16) Ypos(i16) Zpos(i16) Rot(i16)
  monster t @ 8 + 56*PatCount + 116*t (116B, SB2_MON_PARM): the fields we edit are
    MaxHP@12(u16) MaxMP@14(u16) WinGil@16(u16) WinExp@18(u16) WinItems@20(4B) StealItems@24(4B)
    Element{Speed@52,Str@53,Mag@54,Spr@55} Level@64(1)

A stat edit targets the slot's TYPE (SB2_MON_PARM is per type), so two slots sharing a type share stats
(a real FF9 constraint) -- the editor warns when a type is tuned twice.
"""
from __future__ import annotations

import struct

from .. import items

_HDR = 8
_PAT = 56
_MON = 116
_PUT = 12
_FLG_TARGETABLE = 1     # SB2_PUT.FLG_TARGETABLE -- the enemy can be selected/attacked (FLG_MULTIPART=2)

# SB2_MON_PARM field -> (offset, struct-fmt). Only the author-facing, raw17-safe fields.
_MON_FIELDS = {
    "hp": (12, "<H"), "mp": (14, "<H"), "gil": (16, "<H"), "exp": (18, "<H"),
    "speed": (52, "<B"), "strength": (53, "<B"), "magic": (54, "<B"), "spirit": (55, "<B"),
    "level": (64, "<B"),
}
_MON_INT_MAX = {"<H": 0xFFFF, "<B": 0xFF}


class SceneEditError(ValueError):
    pass


def parse_counts(raw16: bytes):
    """(PatCount, TypCount, AtkCount) from the header."""
    if len(raw16) < _HDR:
        raise SceneEditError("raw16 too short")
    return raw16[1], raw16[2], raw16[3]


def _mon_base(patcount: int) -> int:
    return _HDR + _PAT * patcount


def apply_scene_edits(raw16: bytes, scene: dict) -> tuple[bytes, list[str]]:
    """Patch ``raw16`` with a battle.toml ``[scene]`` dict. Returns (patched_bytes, warnings).

    SPAWN COMPOSITION (``monster_count`` set) re-composes a DETERMINISTIC fight: it writes the SAME
    composition (count + per-slot type/placement) to EVERY pattern, so whichever pattern the engine rolls
    yields the user's fight -- and ``build.py`` re-authors the battle eb's Main_Init to match (one enemy-AI
    object per slot), which is what lets a mint exceed the donor's natural enemy count (up to the engine's
    hard cap of 4) using the scene's existing types. Without ``monster_count`` it only TUNES the one
    ``pattern`` (positions/stats/rewards/camera), leaving the composition + the eb untouched.
    """
    patcount, typcount, _atk = parse_counts(raw16)
    b = bytearray(raw16)
    warnings: list[str] = []
    enemies = scene.get("enemy", [])

    cam = None
    if "camera" in scene:
        cam = int(scene["camera"])
        if not 0 <= cam <= 255:
            raise SceneEditError(f"[scene] camera {cam} out of range (0-2 = a fixed PSX pose, >=3 random)")
    mc = None
    if "monster_count" in scene:
        mc = int(scene["monster_count"])
        if not 1 <= mc <= 4:
            raise SceneEditError(f"[scene] monster_count {mc} out of range (1-4; engine hard cap)")

    # spawn composition -> apply to ALL patterns (uniform/deterministic); else tune the one selected pattern
    if mc is not None:
        pats = list(range(patcount))
    else:
        p = int(scene.get("pattern", 0))
        if not 0 <= p < patcount:
            raise SceneEditError(f"[scene] pattern {p} out of range (this scene has {patcount} pattern(s))")
        pats = [p]

    mon_base = _mon_base(patcount)
    for pat in pats:
        pat_off = _HDR + _PAT * pat
        if cam is not None:
            b[pat_off + 2] = cam
        if mc is not None:
            b[pat_off + 1] = mc
        for e in enemies:
            _edit_placement(b, pat_off, e, typcount)
        count = b[pat_off + 1]                              # every ACTIVE slot must be a valid, hittable type
        for s in range(count):
            po = pat_off + 8 + _PUT * s
            if b[po] >= typcount:
                raise SceneEditError(f"active slot {s} (monster_count {count}) has enemy type {b[po]} >= "
                                     f"TypCount {typcount}; give it a 'type' of 0-{typcount - 1}")
            if not (b[po + 1] & _FLG_TARGETABLE):
                raise SceneEditError(f"active slot {s} (monster_count {count}) is not targetable -- set its "
                                     f"'type' so it becomes a normal attackable enemy (else the fight can't end)")

    # stats / rewards are per TYPE (one shared block; same-type slots share it) -> apply once (slot types are
    # uniform across patterns, so resolve each enemy's type from the representative pattern).
    rep = _HDR + _PAT * pats[0] + 8
    tuned_types: dict[int, int] = {}
    for e in enemies:
        slot = int(e["slot"])
        stat_keys = [k for k in e if k in _MON_FIELDS or k in ("drop", "steal")]
        if not stat_keys:
            continue
        type_no = b[rep + _PUT * slot]
        if type_no in tuned_types and tuned_types[type_no] != slot:
            warnings.append(f"slots {tuned_types[type_no]} and {slot} share enemy type {type_no}; "
                            f"their stats/rewards are the SAME data -- slot {slot} wins")
        tuned_types.setdefault(type_no, slot)
        if type_no >= typcount:
            raise SceneEditError(f"slot {slot} references type {type_no} >= TypCount {typcount}")
        mon_off = mon_base + _MON * type_no
        for k in stat_keys:
            if k in _MON_FIELDS:
                off, fmt = _MON_FIELDS[k]
                v = int(e[k])
                if not 0 <= v <= _MON_INT_MAX[fmt]:
                    raise SceneEditError(f"slot {slot} {k}={v} out of range (0-{_MON_INT_MAX[fmt]})")
                struct.pack_into(fmt, b, mon_off + off, v)
            else:  # drop / steal: 4 item slots (id/name; 255 = none)
                base = mon_off + (20 if k == "drop" else 24)
                for i, iid in enumerate(_resolve_items(e[k], slot, k)):
                    b[base + i] = iid
    return bytes(b), warnings


def _edit_placement(b: bytearray, pat_off: int, e: dict, typcount: int) -> None:
    """Apply one [[scene.enemy]]'s slot TYPE + placement (pos/y/rot) within a single pattern."""
    if "slot" not in e:
        raise SceneEditError("[[scene.enemy]] needs a 'slot' (0-3, the placement in the pattern)")
    slot = int(e["slot"])
    if not 0 <= slot < 4:
        raise SceneEditError(f"[[scene.enemy]] slot {slot} out of range (0-3)")
    put_off = pat_off + 8 + _PUT * slot
    if "type" in e:
        t = int(e["type"])
        if not 0 <= t < typcount:
            raise SceneEditError(f"slot {slot} type {t} out of range (0-{typcount - 1}); must be an enemy "
                                 f"type ALREADY in this scene, so the forked raw17/GEO/AI covers it")
        b[put_off] = t
        b[put_off + 1] = _FLG_TARGETABLE                   # normal, targetable, single-part enemy
        # GROUND it: default an activated slot's height to slot 0's Ypos (a real on-ground enemy). Explicit y wins.
        struct.pack_into("<h", b, put_off + 6, struct.unpack_from("<h", b, pat_off + 8 + 6)[0])
    if "pos" in e:
        pos = list(e["pos"])
        if len(pos) not in (2, 3):
            raise SceneEditError(f"[[scene.enemy]] slot {slot}: pos must be [x, z] or [x, y, z]")
        struct.pack_into("<h", b, put_off + 4, _clamp_i16(int(pos[0])))    # Xpos
        struct.pack_into("<h", b, put_off + 8, _clamp_i16(int(pos[-1])))   # Zpos
        if len(pos) == 3:
            struct.pack_into("<h", b, put_off + 6, _clamp_i16(int(pos[1])))  # Ypos (height)
    if "y" in e:
        struct.pack_into("<h", b, put_off + 6, _clamp_i16(int(e["y"])))
    if "rot" in e:
        struct.pack_into("<h", b, put_off + 10, _clamp_i16(int(e["rot"])))


def _clamp_i16(v: int) -> int:
    return max(-32768, min(32767, v))


def _resolve_items(value, slot: int, key: str) -> list[int]:
    if not isinstance(value, list) or len(value) != 4:
        raise SceneEditError(f"slot {slot} {key} must be a list of exactly 4 items "
                             f"(name/id; use \"none\" or 255 for an empty slot)")
    out = []
    for it in value:
        if isinstance(it, str) and it.strip().lower() in ("none", "", "-"):
            out.append(255)
        else:
            out.append(items.resolve(it))
    return out


def validate_scene(raw16: bytes, scene: dict) -> list[str]:
    """Offline problems (empty => OK). Re-runs the edit on a copy to surface any error as a message."""
    try:
        _, warnings = apply_scene_edits(raw16, scene)
        return []
    except (SceneEditError, ValueError) as e:
        return [str(e)]
