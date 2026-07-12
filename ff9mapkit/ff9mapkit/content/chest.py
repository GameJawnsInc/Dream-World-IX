"""Inject a real openable TREASURE CHEST -- one object whose pose is save-flag-gated (closed/open) and
whose press handler animates the lid, gives a fixed item or gil, shows a "Received X" box, and latches the
flag so it STAYS OPEN across saves.

Byte-grounded on real FF9 chests (field 200 entry 9; field 407 entries 12/22 -- model 75 = GEO_ACC_F0_TBX),
decoded opcode-for-opcode. Init (tag 0): CreateObject + TurnInstant + SetObjectLogicalSize(1,40,45) [the
collision box] + SetStandAnimation(7340) + SetObjectFlags(5) + SetHeadFocusMask(2,0) + a TWO-ARM pose branch
on a save-persistent GLOB_BOOL opened-flag -> SetStandAnimation(OPEN 7338) when SET / (CLOSED 7339) when
CLEAR + SetObjectFlags(49) [show + can't-walk-through(16) + don't-hide(32) = the chest's solid collision] +
EnableHeadFocus(0). The model is ALWAYS shown; only the pose differs, so a re-entered / reloaded field
re-poses the chest OPEN (the flag persists in gEventGlobal across saves) with zero per-visit bookkeeping.

The open handler runs in the chest's OWN object context (so RunAnimation animates the chest's own model -- a
separate region has no model and could not). SetObjectFlags bits (EventEngine.DoEventCode CFLAG 0x93:2040):
1 show, 2 collide-player, 4 collide-NPC, 8 disable-talk, 16 can't-walk-through, 32 don't-hide.

Fidelity note: real chests put the open in the object's tag-2 RANGE function and gate the ``Bubble`` "!" on
the opened-flag; the kit uses the object's tag-3 talk handler (press X while near) and instead sets the
**disable-talk** flag (bit 8) once opened, so a looted chest shows no "!" and ignores presses -- the same
"approach + press once, then inert" behaviour, a different dispatch tag.
"""
from __future__ import annotations

import struct

from .. import items as _items
from ..eb import edit, opcodes
from . import event as _event
from . import npc as _npc
from . import region as _region

CHEST_MODEL = 75              # GEO_ACC_F0_TBX (the kit prop archetype "chest")
CLOSED_POSE = 7339            # SetStandAnimation rest pose when CLOSED
OPEN_POSE = 7338             # ... when OPEN (after looting)
NEUTRAL_POSE = 7340          # the transitional default the real Init sets before the pose branch
OPEN_ANIM = 7336             # the RunAnimation lid-open clip
CHEST_LOGICAL_SIZE = (1, 40, 45)      # SetObjectLogicalSize -- the real chest's collision box
CHEST_FLAGS_INIT = 5         # SetObjectFlags initial: show(1) + collide-NPC(4) (matches the real Init)
CHEST_FLAGS_CLOSED = 49      # show(1) + can't-walk-through(16) + don't-hide(32): solid + talkable (-> "!")
CHEST_FLAGS_OPEN = 57       # CHEST_FLAGS_CLOSED + disable-talk(8): solid but NO "!" / inert once looted
CHEST_FLAG_CLASS = _region.GLOB_BOOL   # 0xC4 -- save-persistent gEventGlobal bool
# The opened-flag is REQUIRED (no auto-allocation): inject_chest takes it as `flag_idx`, and build.validate
# enforces a DEFINED flag in the safe custom band [flags.FIRST_SAFE_FLAG, CHOICE_SCRATCH_FLOOR) -- so it can't
# shift on reorder (a positional bit would) or collide with FF9's own chest bitfield ([8376, 8511]). A named
# [[flag]] is the ergonomic, campaign-unique choice.

SET_MODEL = 0x2F
SET_OBJECT_LOGICAL_SIZE = 0x4B
SET_OBJECT_FLAGS = 0x93
SET_HEAD_FOCUS_MASK = 0x8B
ENABLE_HEAD_FOCUS = 0x47
SET_ANIMATION_FLAGS = 0x3F
RUN_SOUND_CODE3 = 0xC8       # RunSoundCode3(bank, sound_id, p1, p2, p3) -- the SFX op the real chest uses
LID_SFX = (637, 638)         # the two lid-creak sound ids the real chest plays
ITEM_JINGLE = 108            # the item-get jingle the real chest plays when the Received box appears
SFX_BANK = 53248             # 0xD000 -- the sound bank the chest SFX live in
SFX_PARAMS = (0, 128, 125)   # the pan/volume params (byte-faithful to fields 200/407)

# The 4 FF9 treasure-chest models (GEO_ACC_F0..F3_TBX) and their per-model animation ids -- decoded byte-for-byte
# from real fields (the Init's [neutral, open, closed] SetStandAnimation order + the tag-2 lid RunAnimation) and
# independently cross-verified across many fields, anchored to the in-game-proven F0 chest. The chest OBJECT is
# otherwise byte-identical across models (same collision LogSize 1,40,45, flags 5->49, opened-flag branch), so
# only the model id + these 4 animation ids vary. Two clip schemes: F0/F2 share the 73xx clips, F1/F3 share the
# low ids. ★ Extracting the FBX+textures from p0data (models/1/<id>/) confirms only TWO DISTINCT LOOKS: F1 (91) and
# F3 (702) are byte-identical (same mesh + both textures); F0 (75) and F2 (701) share the mesh + one texture and
# differ ONLY in F2's other texture being a ~magenta UNUSED dummy -> renders the same as F0. F2/F3 are per-zone
# duplicate ids kept here for fidelity; author with F0/F1 for the two real looks. tuple = (model_id, neutral, open, closed, lid).
CHEST_VARIANTS = {
    "F0": (75,  7340, 7338, 7339, 7336),   # GEO_ACC_F0_TBX -- the default wooden chest (in-game proven)
    "F1": (91,  4,    1,    3,    22),      # GEO_ACC_F1_TBX -- the 2nd real look
    "F2": (701, 7340, 7338, 7339, 7336),   # GEO_ACC_F2_TBX -- F0 with a magenta dummy texture (looks identical to F0)
    "F3": (702, 4,    1,    3,    22),      # GEO_ACC_F3_TBX -- byte-identical to F1
}
_VARIANT_BY_MODEL = {tup[0]: tup for tup in CHEST_VARIANTS.values()}    # model id -> the same 5-tuple


def resolve_chest_variant(model=None):
    """Resolve a ``[[chest]] model`` to ``(model_id, neutral_pose, open_pose, closed_pose, lid_anim)``.
    ``model`` is a variant NAME ("F0".."F3", case-insensitive), a raw model id (75/91/701/702), or ``None``
    (= the default F0 wooden chest). Raises ``ValueError`` on an unknown model -- its open/closed/lid animation
    ids aren't known, and a bare model swap (keeping F0's 73xx clips) would play the wrong / no lid + pose."""
    if model is None or model == "":
        return CHEST_VARIANTS["F0"]
    if isinstance(model, str) and not model.strip().lstrip("-").isdigit():
        key = model.strip().upper()
        if key not in CHEST_VARIANTS:
            raise ValueError(f"unknown chest model {model!r} -- use one of {sorted(CHEST_VARIANTS)} "
                             f"(the F0..F3 treasure-chest variants) or a raw model id {sorted(_VARIANT_BY_MODEL)}")
        return CHEST_VARIANTS[key]
    mid = int(model)
    if mid not in _VARIANT_BY_MODEL:
        raise ValueError(f"chest model id {mid} has no known open/closed/lid animations -- use a TBX chest "
                         f"variant {sorted(CHEST_VARIANTS)} (ids {sorted(_VARIANT_BY_MODEL)})")
    return _VARIANT_BY_MODEL[mid]


def chest_lid_sfx() -> bytes:
    """The lid-creak open SFX, byte-faithful to the real chest (fields 200/407): SetAnimationFlags(1,0) +
    two RunSoundCode3 (bank 53248, ids 637 then 638)."""
    out = opcodes.encode(SET_ANIMATION_FLAGS, 1, 0)
    for sid in LID_SFX:
        out += opcodes.encode(RUN_SOUND_CODE3, SFX_BANK, sid, *SFX_PARAMS)
    return out


def build_chest_init(*, x: int, z: int, flag_idx: int, model: int = CHEST_MODEL, animset: int | None = None,
                     face: int = 0, neutral_pose: int = NEUTRAL_POSE, open_pose: int = OPEN_POSE,
                     closed_pose: int = CLOSED_POSE) -> bytes:
    """The chest Init (tag 0), opcode-faithful to the real chest, with the SAVABLE open-state: a two-arm
    pose+flags branch on the opened flag -- the OPEN pose + the inert(disable-talk) flags when SET, the
    CLOSED pose + the talkable flags when CLEAR. The collision (size + flags) is unconditional -- and so is
    the Init itself: a story-gated (appearance-flag) chest guards its ``InitObject`` CALL SITE instead
    (``inject_chest``), per the OBJECT-INIT GATE LAW on :func:`ff9mapkit.content.region.guarded_call` (an
    Init returning before ``SetModel`` loads the object permanently HIDDEN)."""
    animset_v, _hf, _ls = _npc._npc_object_params(model, animset)
    parts = [
        _npc._d9_const(0, x), _npc._d9_const(4, z), _npc._d9_const(6, face), _npc._d9_const(2, 0),
        bytes([SET_MODEL, 0x00]) + struct.pack("<H", int(model) & 0xFFFF) + bytes([animset_v & 0xFF]),
        _npc._CREATE_OBJECT, _npc._TURN_INSTANT,
        opcodes.encode(SET_OBJECT_LOGICAL_SIZE, *CHEST_LOGICAL_SIZE),     # the collision box
        opcodes.set_stand_animation(neutral_pose),
        opcodes.encode(SET_OBJECT_FLAGS, CHEST_FLAGS_INIT),
        opcodes.encode(SET_HEAD_FOCUS_MASK, 2, 0),
        _region.if_else(_region.cond_truthy(CHEST_FLAG_CLASS, flag_idx),
                        opcodes.set_stand_animation(open_pose) + opcodes.encode(SET_OBJECT_FLAGS, CHEST_FLAGS_OPEN),
                        opcodes.set_stand_animation(closed_pose) + opcodes.encode(SET_OBJECT_FLAGS, CHEST_FLAGS_CLOSED)),
        opcodes.encode(ENABLE_HEAD_FOCUS, 0),
        opcodes.RETURN,
    ]
    return b"".join(parts)


def build_chest_open(flag_idx: int, *, give: bytes, received_text_id: int, payload_value: int,
                     open_anim: int = OPEN_ANIM, open_pose: int = OPEN_POSE) -> bytes:
    """The chest press handler (tag 3): no-op if already opened, else animate the lid open, give the
    payload, show the Received box, latch the opened flag, and set the disable-talk flag (so it shows no
    more "!" and ignores presses for the rest of the visit -- the Init handles it on the next load)."""
    return b"".join([
        _region.flag_gate(CHEST_FLAG_CLASS, flag_idx, require_set=False),    # already opened -> return
        chest_lid_sfx(),                                                     # the lid-creak SFX (637/638)
        opcodes.run_animation(open_anim), opcodes.wait_animation(),          # lid opens (on the chest's own model)
        opcodes.set_stand_animation(open_pose),                             # hold the open pose for this visit
        opcodes.encode(RUN_SOUND_CODE3, SFX_BANK, ITEM_JINGLE, *SFX_PARAMS),  # the item-get jingle (with the box)
        give,                                                               # AddItem / AddGil
        opcodes.set_text_variable(0, payload_value),                        # bind the item/amount for the box
        opcodes.window_sync(7, 0, received_text_id),                        # window TYPE 7 = the "Received X" box
        _region.set_var(CHEST_FLAG_CLASS, flag_idx, 1),                     # latch the opened flag (save-backed)
        opcodes.encode(SET_OBJECT_FLAGS, CHEST_FLAGS_OPEN),                 # disable talk -> no "!" the rest of the visit
        opcodes.RETURN,
    ])


def inject_chest(data, x, z, *, flag_idx: int, item=None, gil=None, count: int = 1,
                 received_text_id: int = 62, model="F0", face: int = 0, gate=None,
                 reserve_party_band: bool = False, spawn_wait_n: int = 2, spawn_wait_occurrence: int = 0):
    """Inject an openable, savable treasure chest at world (x, z) -- ONE object (tag 0 Init + tag 3 open).
    Exactly one of ``item`` (id/name + ``count``) or ``gil`` (amount). ``flag_idx`` (a GLOB_BOOL save index)
    is the opened bit -- it drives the Init open/closed pose+flags and the open handler's once-guard + latch.
    ``model`` picks the chest VARIANT (a name "F0".."F3" or a raw id 75/91/701/702 -- :func:`resolve_chest_variant`
    supplies its own open/closed/neutral pose + lid clip). ``face`` rotates the model; ``gate`` =
    ``(flag_index, require_set)`` makes the chest's APPEARANCE story-gated. Returns new ``.eb`` bytes."""
    if (item is None) == (gil is None):
        raise ValueError("inject_chest needs exactly one of item= or gil=")
    model_id, neutral_pose, open_pose, closed_pose, lid_anim = resolve_chest_variant(model)
    if item is not None:
        item_id = _items.resolve(item)
        give, payload = _event.give_item(item_id, count), item_id
    else:
        give, payload = _event.give_gil(int(gil)), int(gil)
    init = build_chest_init(x=int(x), z=int(z), flag_idx=flag_idx, model=model_id, face=int(face),
                            neutral_pose=neutral_pose, open_pose=open_pose, closed_pose=closed_pose)
    openb = build_chest_open(flag_idx, give=give, received_text_id=received_text_id, payload_value=payload,
                             open_anim=lid_anim, open_pose=open_pose)
    if len(openb) < 9:                              # IsActuallyTalkable polls tag3[ip+7/8]; keep it >= 9 bytes
        openb += b"\x00" * (9 - len(openb))
    table_len = 2 * 4
    table = struct.pack("<HH", 0, table_len) + struct.pack("<HH", 3, table_len + len(init))
    entry = bytes([_npc.NPC_ENTRY_TYPE, 2]) + table + init + openb     # type-2 object: tag 0 + tag 3
    from . import object as _object
    out, slot = _object.seat_entry(data, entry, reserve_party_band=reserve_party_band)
    if gate is not None:                            # appearance gate -> the call-site guard (the stock idiom)
        gf, gset = gate
        block = _region.guarded_call([(_region.cond_truthy(_region.GLOB_BOOL, int(gf)), bool(gset))],
                                     opcodes.init_object(slot, 0))
        return edit.activate_block(out, block)
    return edit.activate(out, opcodes.init_object(slot, 0), spawn_wait_n=spawn_wait_n,
                         spawn_wait_occurrence=spawn_wait_occurrence)
