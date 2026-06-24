"""Place a static set-dressing PROP -- the real FF9 prop recipe (no emulation; replicated from bytes).

A prop is the NPC object MINUS the character behaviours: it holds a single static pose and does NOT turn
to face the player. Verified byte-for-byte against shipping fields -- the save-moogle (field 300, entry 5)
and the chest (field 115, entry 9) -- whose Init does:

    SetModel + CreateObject + SetStandAnimation(<pose>) + SetObjectFlags(..) + EnableHeadFocus(0)

`EnableHeadFocus(0)` (engine source: "Enable or disable the character turning his head toward an active
object") is exactly the switch that kills the turn-to-player behaviour an NPC has. So a prop is just the
proven NPC injection (:func:`content.npc.inject_npc`) with the static pose in all gesture slots plus that
tail appended to Init -- we add nothing the engine doesn't already do for its own props.
"""
from __future__ import annotations

from ..eb import EbScript, opcodes
from .npc import ANIM_ORDER, inject_npc

ENABLE_HEAD_FOCUS = 0x47    # "Enable or disable the character turning his head toward an active object"
TURN_INSTANT = 0x36
ATTACH_OBJECT = 0x4C        # "Attach an object to another one" -- AttachObject(attachedUid, carryingUid, bone)
SET_OBJECT_FLAGS = 0x93     # bits: 1 show model, 2 collide player, 4 collide NPC, 8 disable talk
HELD_FLAGS = 7              # show + collide + collideNPC -- the flags the shipping held cup sets
# NB: do NOT blanket-apply SetObjectFlags here. Per the engine (EventEngine.DoEventCode, CFLAG 0x93) the
# flag bits are {1: show model, 2: collide player, 4: collide NPC, 8: disable talk, ...} and it REPLACES
# the object's low 6 bits. The shipping props' SetObjectFlags(14) (= 2+4+8) omits bit 1 -> "show model"
# off -> the prop vanishes (in-game-verified: adding it hid all four props). Our prop is a cloned player
# object that is already shown + collidable, so we only need to kill head-tracking. A future
# interactivity option can add a SHOW-preserving flag (e.g. 1|8 to also disable the talk prompt).


def prop_init_tail(face: int | None = None) -> bytes:
    """The bytes a prop's Init runs after CreateObject: disable head-tracking (+ an optional instant
    facing). Mirrors the shipping save-moogle / chest objects minus the model-hiding SetObjectFlags."""
    tail = opcodes.encode(ENABLE_HEAD_FOCUS, 0)                 # EnableHeadFocus(0): no turn-to-face
    if face:
        tail += opcodes.encode(TURN_INSTANT, int(face) & 0xFF)  # TurnInstant(face)
    return tail


def inject_prop(data, x: int, z: int, *, model: int, pose: int, face: int | None = None,
                dialogue_text_id: int | None = None, slot: int | None = None,
                attach_to: int | None = None, bone: int = 11,
                spawn_wait_n: int = 2, spawn_wait_occurrence: int = 0,
                gate_flag: int | None = None, gate_require_set: bool = True,
                reserve_party_band: bool = False) -> bytes:
    """Place a prop ``model`` at world (x, z), held at ``pose`` (an animation id), head-tracking OFF.

    ``attach_to`` (a carrying object's uid = its entry slot) binds this prop to that object's ``bone``
    so it follows it -- the real held-item recipe ``AttachObject(self_uid, carrier_uid, bone)`` (bone
    defaults to 11, the right hand the shipping cup uses). The prop's own uid IS its entry slot, so the
    slot is resolved up front. ``dialogue_text_id`` makes it readable; ``face``/``gate_flag`` as usual.
    ``reserve_party_band`` (the VERBATIM-fork path) seats the prop BELOW the party-character band (only for
    a STATIC prop; an ``attach_to`` held item resolves its slot up front and is unsupported there).
    Returns new ``.eb`` bytes."""
    anims = {k: pose for k in ANIM_ORDER}                       # all five gesture slots = the (held) pose
    if attach_to is not None:                                   # ATTACHED: bind to the carrier's bone
        if reserve_party_band:
            raise ValueError("inject_prop: attach_to (held item) is not supported with reserve_party_band "
                             "(its uid is its slot, resolved before the band-aware insert)")
        if slot is None:
            slot = EbScript.from_bytes(data).first_free_slot()  # the prop's uid == its slot (= attachedUid)
        tail = opcodes.encode(ATTACH_OBJECT, slot, int(attach_to), int(bone))
        tail += opcodes.encode(SET_OBJECT_FLAGS, HELD_FLAGS)    # show + collide (like the shipping cup)
    else:                                                       # STATIC: just kill head-tracking
        tail = prop_init_tail(face)
    # a non-interactive prop is BARE (Init-only, no tag-3 talk func -> the engine's IsActuallyTalkable
    # short-circuits instead of indexing past it = no per-frame IndexOutOfRange). A prop with dialogue
    # keeps a real tag-3 WindowSync so it stays readable.
    return inject_npc(data, x, z, model=model, anims=anims,
                      talk_text_id=(dialogue_text_id if dialogue_text_id is not None else 62),
                      init_tail=tail, slot=slot, bare=(dialogue_text_id is None),
                      spawn_wait_n=spawn_wait_n, spawn_wait_occurrence=spawn_wait_occurrence,
                      gate_flag=gate_flag, gate_require_set=gate_require_set,
                      reserve_party_band=reserve_party_band)
