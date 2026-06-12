"""Full read-only codec for a BTL_SCENE ``dbfile0000.raw16`` -- the per-scene binary that holds every
enemy's stats / affinities / rewards + the spawn patterns + the enemy attack table.

This is the *parse* side of battle tuning (the SCANNER): it reads the WHOLE scene into named records so a
tool (or the offline lint suite) can SEE every field -- not just the ~9 that :mod:`scene_data` byte-patches.
:func:`serialize_scene` re-emits byte-for-byte, including the engine-ignored TAIL after the attack block, so
``serialize_scene(parse_scene(x)) == x`` is the golden round-trip that PROVES the offset map (and converts
the kit's "copy-identity" forks into "codec-identity").

Layout authority = Memoria ``Global/BTL_SCENE.cs`` (the ``ReadBattleScene`` BinaryReader order) and
``Global/SB2/SB2_MON_PARM.cs``. All multi-byte fields are little-endian. NOTE the disk widths differ from the
runtime struct: e.g. MaxHP/PhysicalDefence are widened to UInt32/Int32 in memory but are u16/u8 ON DISK
(`ReadUInt16`/`ReadByte`) -- this codec follows the DISK widths.

This file is a pure codec (no Square-Enix bytes); it reads bytes the caller supplies (a forked donor read
live from the install) and ships nothing.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass, field as _dcfield

_HDR = 8
_PAT = 56
_MON = 116
_PUT = 12
_ATK = 16

# ---- struct formats (little-endian; verified to sum to the fixed record sizes) -------------------------
# SB2_PATTERN (56B): Rate,MonsterCount,Camera,Pad0 (4B) + AP (u32) + 4x SB2_PUT (12B each).
_PAT_FMT = "<4BI" + "4B4h" * 4
# SB2_MON_PARM (116B): the exact ReadBattleScene order (BTL_SCENE.cs:54-122).
_MON_FMT = (
    "<3I"      # ResistStatus, AutoStatus, InitialStatus            (u32 BattleStatus masks)  @0
    "4H"       # MaxHP, MaxMP, WinGil, WinExp                                                  @12
    "4B"       # WinItems[4]  (drop item ids; 255=none)                                        @20
    "4B"       # StealItems[4]                                                                 @24
    "H"        # Radius                                                                        @28
    "h"        # Geo  (i16, model)                                                             @30
    "6H"       # Mot[6]  (movement/attack anim ids)                                            @32
    "2H"       # Mesh[2]                                                                       @44
    "H"        # Flags  (per-enemy MON flags)                                                  @48
    "H"        # AP  (per-type; the GAMEPLAY AP is the pattern AP)                             @50
    "8B"       # Element: Speed,Strength,Magic,Spirit, pad,trans,cur_capa,max_capa            @52
    "5B"       # GuardElement,AbsorbElement,HalfElement,WeakElement, Level                     @60
    "7B"       # Category,HitRate,PhysicalDefence,PhysicalEvade,MagicalDefence,MagicalEvade,BlueMagic @65
    "4B"       # Bone[4]                                                                       @72
    "H"        # DieSfx                                                                        @76
    "2B"       # Konran, MesCnt                                                                @78
    "6B"       # IconBone[6]                                                                   @80
    "6b"       # IconY[6]  (sbyte)                                                             @86
    "6b"       # IconZ[6]  (sbyte)                                                             @92
    "3H"       # StartSfx, ShadowX, ShadowZ                                                    @98
    "2B"       # ShadowBone, WinCard                                                           @104
    "2h"       # ShadowOfsX, ShadowOfsZ  (i16)                                                 @106
    "2B"       # ShadowBone2, Pad0                                                             @110
    "2H"       # Pad1, Pad2                                                                    @112
)
# AA_DATA (16B): packed info (u32) + 8 single bytes + Vfx2 (u16) + Name (u16).
_ATK_FMT = "<I8B2H"

assert struct.calcsize(_PAT_FMT) == _PAT
assert struct.calcsize(_MON_FMT) == _MON
assert struct.calcsize(_ATK_FMT) == _ATK


class SceneCodecError(ValueError):
    pass


@dataclass
class Put:
    """SB2_PUT -- one formation slot's enemy type + placement."""
    type_no: int
    flags: int
    pease: int
    pad: int
    x: int
    y: int
    z: int
    rot: int

    @property
    def targetable(self) -> bool:
        return bool(self.flags & 1)        # FLG_TARGETABLE


@dataclass
class Pattern:
    """SB2_PATTERN -- one formation (spawn weight, count, camera, AP, 4 placements)."""
    rate: int
    monster_count: int
    camera: int
    pad0: int
    ap: int
    puts: list                              # 4x Put


@dataclass
class MonParm:
    """SB2_MON_PARM -- one enemy TYPE's full record (every disk field, named).

    The gameplay-relevant fields are scalars; cosmetic/pad/array fields are kept verbatim (so the record
    round-trips) but rarely interesting. Element masks (`guard/absorb/half/weak_element`) and the status
    masks (`resist/auto/initial_status`) are raw ints -- decode with :mod:`scene_data` helpers."""
    resist_status: int
    auto_status: int
    initial_status: int
    hp: int
    mp: int
    gil: int
    exp: int
    drop: tuple                             # WinItems[4]
    steal: tuple                            # StealItems[4]
    radius: int
    geo: int
    mot: tuple                              # [6]
    mesh: tuple                             # [2]
    flags: int
    ap: int
    speed: int
    strength: int
    magic: int
    spirit: int
    elem_pad: int
    trans: int
    cur_capa: int
    max_capa: int
    guard_element: int
    absorb_element: int
    half_element: int
    weak_element: int
    level: int
    category: int
    hit_rate: int
    phys_def: int
    phys_evade: int
    mag_def: int
    mag_evade: int
    blue_magic: int
    bone: tuple                             # [4]
    die_sfx: int
    konran: int
    mes_cnt: int
    icon_bone: tuple                        # [6]
    icon_y: tuple                           # [6] sbyte
    icon_z: tuple                           # [6] sbyte
    start_sfx: int
    shadow_x: int
    shadow_z: int
    shadow_bone: int
    win_card: int
    shadow_ofs_x: int
    shadow_ofs_z: int
    shadow_bone2: int
    pad0: int
    pad1: int
    pad2: int

    @classmethod
    def unpack(cls, buf, off=0) -> "MonParm":
        t = struct.unpack_from(_MON_FMT, buf, off)
        i = iter(t)
        n = lambda: next(i)
        take = lambda k: tuple(next(i) for _ in range(k))
        return cls(
            resist_status=n(), auto_status=n(), initial_status=n(),
            hp=n(), mp=n(), gil=n(), exp=n(),
            drop=take(4), steal=take(4),
            radius=n(), geo=n(), mot=take(6), mesh=take(2),
            flags=n(), ap=n(),
            speed=n(), strength=n(), magic=n(), spirit=n(),
            elem_pad=n(), trans=n(), cur_capa=n(), max_capa=n(),
            guard_element=n(), absorb_element=n(), half_element=n(), weak_element=n(),
            level=n(), category=n(), hit_rate=n(),
            phys_def=n(), phys_evade=n(), mag_def=n(), mag_evade=n(), blue_magic=n(),
            bone=take(4), die_sfx=n(), konran=n(), mes_cnt=n(),
            icon_bone=take(6), icon_y=take(6), icon_z=take(6),
            start_sfx=n(), shadow_x=n(), shadow_z=n(),
            shadow_bone=n(), win_card=n(), shadow_ofs_x=n(), shadow_ofs_z=n(),
            shadow_bone2=n(), pad0=n(), pad1=n(), pad2=n())

    def pack(self) -> bytes:
        return struct.pack(
            _MON_FMT, self.resist_status, self.auto_status, self.initial_status,
            self.hp, self.mp, self.gil, self.exp, *self.drop, *self.steal,
            self.radius, self.geo, *self.mot, *self.mesh, self.flags, self.ap,
            self.speed, self.strength, self.magic, self.spirit,
            self.elem_pad, self.trans, self.cur_capa, self.max_capa,
            self.guard_element, self.absorb_element, self.half_element, self.weak_element,
            self.level, self.category, self.hit_rate,
            self.phys_def, self.phys_evade, self.mag_def, self.mag_evade, self.blue_magic,
            *self.bone, self.die_sfx, self.konran, self.mes_cnt,
            *self.icon_bone, *self.icon_y, *self.icon_z,
            self.start_sfx, self.shadow_x, self.shadow_z,
            self.shadow_bone, self.win_card, self.shadow_ofs_x, self.shadow_ofs_z,
            self.shadow_bone2, self.pad0, self.pad1, self.pad2)


@dataclass
class Attack:
    """AA_DATA -- one enemy attack (the per-scene atk[] entries; NOT Actions.csv)."""
    info: int                               # packed BattleCommandInfo (Target/VfxIndex/ForDead/... )
    script_id: int
    power: int
    elements: int
    rate: int
    category: int
    add_status: int                         # StatusSetId
    mp: int
    type: int
    vfx2: int
    name: int


@dataclass
class Scene:
    """A parsed BTL_SCENE. ``head`` keeps the 8 header bytes verbatim (Ver/counts/Flags/pad); ``tail`` is
    every byte after the attack block (overwhelmingly zero + engine-ignored, kept for exact re-emit)."""
    head: bytes
    patterns: list                          # list[Pattern]
    monsters: list                          # list[MonParm]
    attacks: list                           # list[Attack]
    tail: bytes = b""

    @property
    def pat_count(self) -> int:
        return self.head[1]

    @property
    def typ_count(self) -> int:
        return self.head[2]

    @property
    def atk_count(self) -> int:
        return self.head[3]

    @property
    def back_attack(self) -> bool:
        return bool(self.scene_flags & 2)

    @property
    def can_escape(self) -> bool:
        return not (self.scene_flags & 32)          # Runaway = (flags & 32) == 0

    @property
    def no_exp(self) -> bool:
        return bool(self.scene_flags & 8)

    @property
    def preemptive(self) -> bool:
        return bool(self.scene_flags & 1)           # SpecialStart

    @property
    def scene_flags(self) -> int:
        return struct.unpack_from("<H", self.head, 4)[0]


def parse_scene(raw16: bytes) -> Scene:
    """Parse a whole ``dbfile0000.raw16`` into a :class:`Scene` (read-only scanner)."""
    if len(raw16) < _HDR:
        raise SceneCodecError("raw16 too short for a header")
    head = bytes(raw16[:_HDR])
    pat_count, typ_count, atk_count = head[1], head[2], head[3]
    need = _HDR + _PAT * pat_count + _MON * typ_count + _ATK * atk_count
    if len(raw16) < need:
        raise SceneCodecError(f"raw16 truncated: need {need} bytes for "
                              f"{pat_count} pattern(s)/{typ_count} type(s)/{atk_count} attack(s), "
                              f"have {len(raw16)}")
    off = _HDR
    patterns = []
    for _ in range(pat_count):
        t = struct.unpack_from(_PAT_FMT, raw16, off)
        rate, mc, cam, p0, ap = t[0], t[1], t[2], t[3], t[4]
        puts = []
        for j in range(4):
            b = 5 + j * 8                                  # 5 scalars before the 4 puts in the tuple
            puts.append(Put(t[b], t[b + 1], t[b + 2], t[b + 3], t[b + 4], t[b + 5], t[b + 6], t[b + 7]))
        patterns.append(Pattern(rate, mc, cam, p0, ap, puts))
        off += _PAT
    monsters = []
    for _ in range(typ_count):
        monsters.append(MonParm.unpack(raw16, off))
        off += _MON
    attacks = []
    for _ in range(atk_count):
        attacks.append(Attack(*struct.unpack_from(_ATK_FMT, raw16, off)))
        off += _ATK
    tail = bytes(raw16[off:])
    return Scene(head=head, patterns=patterns, monsters=monsters, attacks=attacks, tail=tail)


def serialize_scene(scene: Scene) -> bytes:
    """Re-emit a :class:`Scene` to raw16 bytes. ``serialize_scene(parse_scene(x)) == x`` for any valid x."""
    out = bytearray(scene.head)
    for p in scene.patterns:
        puts = []
        for q in p.puts:
            puts += [q.type_no, q.flags, q.pease, q.pad, q.x, q.y, q.z, q.rot]
        out += struct.pack(_PAT_FMT, p.rate, p.monster_count, p.camera, p.pad0, p.ap, *puts)
    for m in scene.monsters:
        out += m.pack()
    for a in scene.attacks:
        out += struct.pack(_ATK_FMT, a.info, a.script_id, a.power, a.elements, a.rate,
                           a.category, a.add_status, a.mp, a.type, a.vfx2, a.name)
    out += scene.tail
    return bytes(out)


def scene_counts(raw16: bytes):
    """(pat_count, typ_count, atk_count) -- a cheap header peek without a full parse."""
    if len(raw16) < _HDR:
        raise SceneCodecError("raw16 too short")
    return raw16[1], raw16[2], raw16[3]
