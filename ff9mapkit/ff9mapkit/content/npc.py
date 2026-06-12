"""Inject an NPC into a field script, and move the player's spawn.

An NPC is built by cloning the field's player object (the entry that calls
``DefinePlayerCharacter``), neutralising it (NOP that opcode so it's an NPC, not a 2nd
player), repositioning it, optionally swapping its model + animations, and adding a
``_SpeakBTN`` (func tag 3) that opens a dialogue window. The clone is appended into a free
entry slot and spawned by overwriting a Main_Init ``Wait(2)`` filler with ``InitObject`` —
shift-free, so nothing else in the script moves.

Offsets are located **symbolically** (via the disassembler / byte patterns), not hardcoded,
so this works on any field whose player object follows the standard template — while
reproducing the proven hand-built results byte-for-byte.
"""

from __future__ import annotations

import struct

from ..binutils import pi16, pu16
from ..eb import EbScript, edit, opcodes
from ..eb.disasm import iter_code
from . import region as _region

# Character presets: (model, animset, {stand, walk, run, left, right} animation ids)
PRESETS = {
    "vivi": (8, 61, {"stand": 148, "walk": 571, "run": 419, "left": 917, "right": 918}),
    "zidane": (None, None, None),  # keep the cloned player's model/anims as-is
}
ANIM_ORDER = ("stand", "walk", "run", "left", "right")

DEFINE_PLAYER = 0x2C
SET_MODEL = 0x2F
SET_STAND_ANIM = 0x33
SET_HEAD_FOCUS_MASK = 0x8B

# The moogle field rigs (GEO_NPC_F0..F5_MOG). Re-skinning the cloned PLAYER template onto a moogle drags
# the template's head-focus mask (97,61 -- a human-rig value), which makes a moogle whip its WHOLE BODY to
# track the player ("head-follow goes crazy"). Real moogle NPCs use a head-ONLY mask (4,1) -- 50/50 in a
# 676-field census, incl. the real Stiltzkin (field 3100, Mognet Central). Normalize moogle re-skins to
# this source value (a same-length, byte-identical-to-source arg patch of the existing SetHeadFocusMask).
MOOGLE_MODELS = frozenset({220, 129, 196, 212, 198, 199})
MOOGLE_HEAD_FOCUS = (4, 1)               # moogle NPCs: head-only focus (50/50 census + the real Stiltzkin)

# ---- faithful NPC synthesis: emit a real standing-NPC object entry FROM SCRATCH (no player clone) --------
# The canonical real-NPC Init shape, byte-verified against Mognet Central (field 3100) standing moogles
# (Mosh / Mogliana) AND the real Stiltzkin: the four position consts -> SetModel -> CreateObject ->
# TurnInstant -> the five movement-anim setters -> SetObjectLogicalSize -> SetAnimationStandSpeed ->
# SetHeadFocusMask -> RETURN. NONE of the player rig's control cruft (DefinePlayerCharacter / EnableMove /
# EnableMenu / the animation-pack RunModelCode·RunSoundCode / SetTriangleFlagMask) leaks in. The Loop is the
# real 2-op standby (yield + jump-back). Per-model values beyond the confirmed moogle set fall back to safe
# defaults here; a baked model->object-params catalog (animset/head-focus/logical-size per model) is the
# planned fast-follow that makes EVERY model byte-faithful, not just moogles.
NPC_ENTRY_TYPE = 2                       # real NPC object entries are type 2 (so is the blank player entry)
DEFAULT_LOGICAL_SIZE = (14, 14, 22)      # collision box; the common real value (moogles + most humans)
MOOGLE_ANIMSET = 50                      # the moogle SetModel animset (real Mosh/Mogliana/Stiltzkin)
DEFAULT_ANIMSET = 50                     # phased fallback for an unknown model (refined by the per-model catalog)
DEFAULT_HEAD_FOCUS = (0, 65)             # non-moogle default: no automatic head-track (static facing)
STAND_SPEED = bytes([0x86, 0x00, 0x0E, 0x10, 0x12, 0x14])    # SetAnimationStandSpeed(14,16,18,20) -- invariant
NPC_STANDBY_LOOP = bytes([0x22, 0x00, 0x01, 0x01, 0xFA, 0xFF])   # yield(1) + JMP -6: the real standby loop
_CREATE_OBJECT = bytes([0x1D, 0x03, 0xD9, 0x00, 0x7F, 0xD9, 0x04, 0x7F])   # CreateObject(D9(0), D9(4))
_TURN_INSTANT = bytes([0x36, 0x01, 0xD9, 0x06, 0x7F])        # TurnInstant(D9(6))
_ANIM_OPS = (0x33, 0x34, 0x35, 0x7A, 0x7B)                   # stand, walk, run, left, right (ANIM_ORDER)


def _d9_const(idx: int, val: int) -> bytes:
    """``SetVar D9(idx) = val`` in the engine's own expression form: 05 D9 idx 7D <i16 LE> 2C 7F."""
    return bytes([0x05, 0xD9, idx, 0x7D]) + struct.pack("<h", int(val)) + bytes([0x2C, 0x7F])


def _anim_op(op: int, anim_id: int) -> bytes:
    """A movement-animation setter: <op> 00 <anim id, u16 LE>."""
    return bytes([op, 0x00]) + struct.pack("<H", int(anim_id) & 0xFFFF)


def _complete_anims(model, anims) -> dict:
    """A full ``{stand, walk, run, left, right}`` clip set -- the from-scratch Init has no cloned clip to keep,
    so every slot must be filled. Uses the given ``anims``, else the Info Hub model->gesture join; a missing
    slot falls back to ``stand``. Raises if the model resolves no animations at all (specify ``anims=``)."""
    a = dict(anims or {})
    if not a:
        from .. import catalog as _catalog
        a = dict(_catalog.npc_anims(int(model)) or {})
    if "stand" not in a or a.get("stand") is None:
        raise ValueError(f"NPC model {model}: no animations resolved -- pass anims={{stand,walk,run,left,right}}")
    return {name: a.get(name) if a.get(name) is not None else a["stand"] for name in ANIM_ORDER}


def _npc_object_params(model, animset):
    """``(animset, head_focus, logical_size)`` for an NPC model -- confirmed moogle values, else defaults
    (the per-model catalog fast-follow will source these faithfully for every model)."""
    is_moog = int(model) in MOOGLE_MODELS
    av = int(animset) if animset is not None else (MOOGLE_ANIMSET if is_moog else DEFAULT_ANIMSET)
    hf = MOOGLE_HEAD_FOCUS if is_moog else DEFAULT_HEAD_FOCUS
    return av, hf, DEFAULT_LOGICAL_SIZE


def build_npc_init(*, model, animset, anims, x: int, z: int, facing: int = 0, y: int = 0,
                   head_focus=DEFAULT_HEAD_FOCUS, logical_size=DEFAULT_LOGICAL_SIZE,
                   init_tail: bytes = b"", gate=None) -> bytes:
    """Emit a faithful standing-NPC Init (func tag 0) from scratch -- the real-NPC opcode shape, NO player
    clone. ``anims`` must hold all five movement clips (see :func:`_complete_anims`). ``gate`` =
    ``(flag_index, require_set)`` prepends a story-flag gate so the object is absent unless the flag is in
    state. ``init_tail`` (the prop recipe: EnableHeadFocus(0) / AttachObject ...) is spliced just before the
    RETURN, applying to the freshly created object."""
    parts = []
    if gate is not None:
        gf, gset = gate
        parts.append(_region.flag_gate(_region.GLOB_BOOL, gf, require_set=gset))
    parts.append(_d9_const(0, x))
    parts.append(_d9_const(4, z))
    parts.append(_d9_const(6, facing))
    parts.append(_d9_const(2, y))
    parts.append(bytes([0x2F, 0x00]) + struct.pack("<H", int(model) & 0xFFFF) + bytes([int(animset) & 0xFF]))
    parts.append(_CREATE_OBJECT)
    parts.append(_TURN_INSTANT)
    for op, name in zip(_ANIM_OPS, ANIM_ORDER):
        parts.append(_anim_op(op, anims[name]))
    parts.append(bytes([0x4B, 0x00, logical_size[0] & 0xFF, logical_size[1] & 0xFF, logical_size[2] & 0xFF]))
    parts.append(STAND_SPEED)
    parts.append(bytes([0x8B, 0x00, head_focus[0] & 0xFF, head_focus[1] & 0xFF]))
    parts.append(bytes(init_tail))
    parts.append(opcodes.RETURN)         # 0x04 -- the real NPC Init terminator
    return b"".join(parts)


def _find_player_entry(eb: EbScript) -> int:
    for e in eb.entries:
        if e.empty:
            continue
        f0 = e.func_by_tag(0)
        if f0 and any(ins.op == DEFINE_PLAYER for ins in eb.instrs(f0)):
            return e.index
    raise ValueError("no player object (DefinePlayerCharacter) found in any entry")


def _func0_locations(eb: EbScript, entry):
    """Return offsets (relative to func0 body start) of the opcodes we patch."""
    f0 = entry.func_by_tag(0)
    base = f0.abs_start
    loc = {"dpc": None, "model": None, "animset": None, "stand": None, "headfocus": None}
    for ins in iter_code(eb.data, f0.abs_start, f0.abs_end):
        if ins.op == DEFINE_PLAYER and loc["dpc"] is None:
            loc["dpc"] = ins.off - base
        elif ins.op == SET_MODEL and loc["model"] is None:
            # SetModel: op, argFlag, model(2), animset(1) -> model@+2, animset@+4
            loc["model"] = ins.off - base + 2
            loc["animset"] = ins.off - base + 4
        elif ins.op == SET_STAND_ANIM and loc["stand"] is None:
            loc["stand"] = ins.off - base + 2   # first anim-setter arg; 4 more follow every 4 bytes
        elif ins.op == SET_HEAD_FOCUS_MASK and loc["headfocus"] is None:
            loc["headfocus"] = ins.off - base + 2   # SetHeadFocusMask: op, flag, arg0, arg1 -> args@+2
    return f0, base, loc


def _find_var_const(body: bytes, var_index: int) -> int:
    """Offset (within body) of the 2-byte const a ``SetVar D9(var_index) = const`` assigns.

    Pattern: 05 D9 <var_index> 7D <lo> <hi> 2C 7F -> the const is the 2 bytes after 0x7D.
    """
    pat = bytes([0x05, 0xD9, var_index, 0x7D])
    i = body.find(pat)
    if i < 0:
        raise ValueError(f"no SetVar D9({var_index}) const found")
    return i + len(pat)


def _player_rig(data) -> tuple:
    """The field player's ``(model, animset, anims)`` -- the default rig for an NPC injected with NO model
    (preserves the pre-template default: a bare ``[[npc]]`` mirrored the field's current player avatar).
    Sourced as a clean model id + clip set read straight from the player Init, NOT a rig clone."""
    eb = EbScript.from_bytes(data)
    entry = eb.entry(_find_player_entry(eb))
    f0, base, loc = _func0_locations(eb, entry)
    if loc["model"] is None:
        raise ValueError("field player has no SetModel -- specify a model for the NPC")
    b = f0.abs_start
    model = int.from_bytes(data[b + loc["model"]:b + loc["model"] + 2], "little")
    animset = data[b + loc["animset"]] if loc["animset"] is not None else None
    anims = None
    if loc["stand"] is not None:
        anims = {name: int.from_bytes(data[b + loc["stand"] + 4 * k:b + loc["stand"] + 4 * k + 2], "little")
                 for k, name in enumerate(ANIM_ORDER)}
    return model, animset, anims


def inject_npc(data, x: int, z: int, *, preset: str | None = None, model=None, animset=None,
               anims=None, talk_text_id: int = 62, slot: int | None = None,
               spawn_wait_n: int = 2, spawn_wait_occurrence: int = 0,
               gate_flag: int | None = None, gate_require_set: bool = True,
               intro: bytes | None = None, speak_body: bytes | None = None,
               init_tail: bytes | None = None, bare: bool = False) -> bytes:
    """Inject an NPC at world (x, z). Returns new .eb bytes.

    ``gate_flag`` (a GlobBool index) makes the NPC conditional: its Init returns early -- so it never
    creates its model and is absent/non-interactable -- unless the flag is in the required state
    (``gate_require_set`` True = appears when the flag is SET, False = when CLEAR). This is the
    standard FF9 way to show/hide an NPC by story state.

    ``intro`` (bytes) is an ACTOR cutscene's gated choreography block (from
    :func:`ff9mapkit.content.cutscene.build_choreography`), spliced into this NPC's Init just before
    its RETURN so it runs in the NPC's own object context (``gExec`` == this NPC) after CreateObject.

    ``speak_body`` (bytes) replaces the default ``_SpeakBTN`` (tag 3) -- pass a dialogue-choice body
    (:func:`ff9mapkit.content.choice.speak_body`) for a talk-to-branch NPC. Must end with a RETURN."""
    if preset is not None:
        model, animset, anims = PRESETS[preset]
    if model is None:
        # no model/preset/archetype -> mirror the field's current player avatar (the pre-template default:
        # a bare [[npc]] / preset "zidane" looked like the player). Clean model+clips, not a rig clone.
        pmodel, pset, panims = _player_rig(data)
        model = pmodel
        animset = animset if animset is not None else pset
        anims = anims or panims
    anims = _complete_anims(model, anims)
    animset_v, head_focus, logical_size = _npc_object_params(model, animset)

    # Init (tag 0): the real-NPC object shape, emitted FROM SCRATCH -- no player clone, no control cruft.
    # The flag `gate` (object absent unless in state) and the prop `init_tail` (EnableHeadFocus(0) /
    # AttachObject) are folded into the Init by build_npc_init.
    body0 = build_npc_init(model=model, animset=animset_v, anims=anims, x=x, z=z,
                           head_focus=head_focus, logical_size=logical_size,
                           init_tail=bytes(init_tail or b""),
                           gate=(gate_flag, gate_require_set) if gate_flag is not None else None)
    # Loop (tag 1): the real 2-op standby. An ACTOR cutscene's `intro` choreography PREPENDS here (NOT the
    # Init): the engine only advances animation frames at loop state 1, so a cutscene baked into the Init
    # (state 2) would glide FROZEN. It self-gates to run once per visit.
    body1 = (bytes(intro) + NPC_STANDBY_LOOP) if intro else NPC_STANDBY_LOOP

    eb = EbScript.from_bytes(data)
    # assemble the entry. A BARE object is Init-only (1 func, tag 0) -- the shipping set-dressing shape; it
    # has NO tag-3 talk func, so the engine's IsActuallyTalkable short-circuits on GetIP(...,3)==nil instead
    # of indexing past a too-short func (no per-frame IndexOutOfRange when the player stands near a prop). A
    # normal NPC keeps Init + Loop + _SpeakBTN (tag 3) so it can be talked to.
    if bare:
        table = struct.pack("<HH", 0, 1 * 4)
        entry_bytes = bytes([NPC_ENTRY_TYPE, 1]) + table + body0
    else:
        f2 = speak_body if speak_body is not None else (opcodes.window_sync(1, 128, talk_text_id) + opcodes.RETURN)
        # IsActuallyTalkable (the per-frame talk-icon poll) blindly reads tag3[ip+7]/[ip+8]; a talk func
        # shorter than 9 bytes indexes PAST the entry buffer -> an IndexOutOfRange every frame the player is
        # near. Real talk funcs are 100+ bytes; pad ours to >= 9 (dead bytes after RETURN -> behaviour same).
        if len(f2) < 9:
            f2 = bytes(f2) + b"\x00" * (9 - len(f2))
        table_len = 3 * 4
        nf0, nf1, nf2 = table_len, table_len + len(body0), table_len + len(body0) + len(body1)
        table = struct.pack("<HH", 0, nf0) + struct.pack("<HH", 1, nf1) + struct.pack("<HH", 3, nf2)
        entry_bytes = bytes([NPC_ENTRY_TYPE, 3]) + table + body0 + bytes(body1) + f2

    # 7) append + spawn (shift-free): overwrite a Main_Init Wait(n) with InitObject(slot,0)
    if slot is None:
        slot = eb.first_free_slot()
    out = edit.append_entry(data, slot, entry_bytes)
    out = edit.activate(out, opcodes.init_object(slot, 0), spawn_wait_n=spawn_wait_n,
                        spawn_wait_occurrence=spawn_wait_occurrence)
    return out


def set_player_spawn(data, x: int, z: int, *, entry_index: int | None = None) -> bytes:
    """Move the player's spawn position (the SetVar D9(0)/D9(4) consts in its Init func)."""
    eb = EbScript.from_bytes(data)
    pe = entry_index if entry_index is not None else _find_player_entry(eb)
    f0 = eb.entry(pe).func_by_tag(0)
    body = bytearray(data[f0.abs_start:f0.abs_end])
    xo, zo = _find_var_const(body, 0), _find_var_const(body, 4)
    abs_x = f0.abs_start + xo
    abs_z = f0.abs_start + zo
    return edit.patch_bytes(edit.patch_bytes(data, abs_x, pi16(x)), abs_z, pi16(z))


def set_player_model(data, model_id: int, anims: dict | None = None, *,
                     animset: int | None = None, entry_index: int | None = None) -> bytes:
    """Re-skin the PLAYER's field avatar to ``model_id`` + its movement ``anims`` -- the `[player] model=`
    option (walk an authored field as a Moogle / any model, the World-Hub PC). Patches the player entry's
    Init ``SetModel`` + the 5 movement-animation setters in place (same byte-exact width as a swap), while
    KEEPING ``DefinePlayerCharacter`` (it is still the player, just a different rig). This is the field-side
    twin of ``playerswap.swap_player`` for a SYNTHESIZED field (vs a fork): the player here is the blank
    field's Zidane, found unambiguously by :func:`_find_player_entry`.

    ``anims`` = ``{stand, walk, run, left, right}`` (from :func:`ff9mapkit.catalog.npc_anims`); a missing key
    keeps the cloned clip. Only MOVEMENT clips are swapped -- a scripted-gesture cutscene would still play
    the donor rig's gesture clips (same caveat as ``--swap-player``); a hub field is free-roam, so clean.
    Raises if the player Init has no ``SetModel`` to re-skin."""
    eb = EbScript.from_bytes(data)
    pe = entry_index if entry_index is not None else _find_player_entry(eb)
    entry = eb.entry(pe)
    f0, _base0, loc = _func0_locations(eb, entry)
    if loc["model"] is None:
        raise ValueError("player Init has no SetModel -- cannot set [player] model")
    body0 = bytearray(data[f0.abs_start:f0.abs_end])
    body0[loc["model"]:loc["model"] + 2] = pu16(int(model_id))
    if animset is not None and loc["animset"] is not None:
        body0[loc["animset"]] = int(animset) & 0xFF
    if anims and loc["stand"] is not None:
        for k, name in enumerate(ANIM_ORDER):
            if name in anims and anims[name] is not None:
                o = loc["stand"] + 4 * k
                body0[o:o + 2] = pu16(int(anims[name]))
    # moogle PC head-focus: a moogle avatar inherits the template's human head mask (97,61) -> a spin-to-
    # face when idle near an NPC. Match the real moogle value (4,1); only for moogle rigs (a human [player]
    # model= keeps its own mask). Same length -> stays in the in-place patch.
    if int(model_id) in MOOGLE_MODELS and loc["headfocus"] is not None:
        body0[loc["headfocus"]:loc["headfocus"] + 2] = bytes(MOOGLE_HEAD_FOCUS)
    return edit.patch_bytes(data, f0.abs_start, bytes(body0))   # same length -> in-place
