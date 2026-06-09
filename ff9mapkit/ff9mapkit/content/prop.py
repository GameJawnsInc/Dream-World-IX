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

from ..eb import opcodes
from .npc import ANIM_ORDER, inject_npc

ENABLE_HEAD_FOCUS = 0x47    # "Enable or disable the character turning his head toward an active object"
TURN_INSTANT = 0x36
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
                spawn_wait_n: int = 2, spawn_wait_occurrence: int = 0,
                gate_flag: int | None = None, gate_require_set: bool = True) -> bytes:
    """Place a prop ``model`` at world (x, z), held at ``pose`` (an animation id), head-tracking OFF.

    ``dialogue_text_id`` makes it readable (a sign, a chest message); omitted = non-interactive (its
    action handler is a no-op RETURN). ``face`` = optional facing (0..255). ``gate_flag`` shows/hides it
    by a story flag, exactly like an NPC. Returns new ``.eb`` bytes."""
    anims = {k: pose for k in ANIM_ORDER}                       # all five gesture slots = the static pose
    if dialogue_text_id is not None:
        speak, ttid = None, dialogue_text_id                    # default WindowSync(text) -> readable
    else:
        speak, ttid = opcodes.RETURN, 62                        # no-op action handler -> not interactive
    return inject_npc(data, x, z, model=model, anims=anims, talk_text_id=ttid,
                      speak_body=speak, init_tail=prop_init_tail(face), slot=slot,
                      spawn_wait_n=spawn_wait_n, spawn_wait_occurrence=spawn_wait_occurrence,
                      gate_flag=gate_flag, gate_require_set=gate_require_set)
