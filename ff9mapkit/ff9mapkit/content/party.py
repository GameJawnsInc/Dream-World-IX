"""Party-membership authoring -- the ``[party]`` block.

Add (or remove) **existing** playable characters to/from the party at field load. This is the authoring
complement to ``import --swap-player`` (which changes who you WALK as): field CONTROL and party STATE are
**decoupled** mechanisms (memory ``project-ff9-pc-party-system``). ``[party]`` touches
``FF9StateGlobal.party.member[]`` -- who's in the MENU + BATTLE -- NOT who you control.

The add is FF9's real JOIN form, an EXPRESSION call ``B_PARTYADD`` (op ``0x6D``): the in-game-proven probe
bytes ``05 C5 93 7D <CharacterOldIndex> 00 6D 2C 7F`` (2026-06-11 -- injecting ``partyadd(Steiner)`` into a
clean field's Main_Init makes the party menu show the new member with starting equipment, because the 12
PLAYER structs exist at boot). The remove is the statement op ``RemoveParty`` (``0xDD``). The sequence is
**prepended to Main_Init** (entry 0 tag 0) like ``[startup]``, so it runs at field load.

★ CAVEAT: a ``SetPartyReserve`` (``0xB4``) that runs AFTER our prepend rebuilds the recruitable roster and
can WIPE the add -- so on a verbatim fork of a field whose Main_Init resets the party, ``build._apply_party``
emits a warning. Pick a field whose Main_Init doesn't reset the party (a synthesized field never does).
Adds are ``.eb``-only (no DLL); FF9 renders only the party LEADER in the field, so an added member shows in
the menu/battle, not as a walking follower.

Author-side only; the ``CharacterOldIndex`` id space (Zidane 0 .. Blank 11) is the same one the party ops
take and ``fork-report``'s Party axis decodes (a test pins this table to ``forkreport.CHAR_OLD_INDEX``).
"""
from __future__ import annotations

from . import region as _region
from ..eb import edit, opcodes

B_PARTYADD = 0x6D          # expression fn (op_binary 109): partyadd(CharacterOldIndex) -> first empty slot
REMOVE_PARTY = 0xDD        # statement op: RemoveParty(CharacterOldIndex)
SET_PARTY_RESERVE = 0xB4   # statement op: SetPartyReserve(mask) -- rebuilds the roster (can wipe a prior add)
PARTY_SCRATCH = 0x93       # MAP_BOOL throwaway index for the partyadd result (matches the proven probe bytes)

# name -> CharacterOldIndex (the .eb id space; NOT the GEO model id, NOT the internal CharacterId enum).
# Kept in lockstep with forkreport.CHAR_OLD_INDEX by test_party (defined here to avoid an import cycle).
CHAR_OLD_INDEX = {0: "Zidane", 1: "Vivi", 2: "Garnet", 3: "Steiner", 4: "Freya", 5: "Quina", 6: "Eiko",
                  7: "Amarant", 8: "Beatrix", 9: "Cinna", 10: "Marcus", 11: "Blank"}
NAME_TO_INDEX = {name.lower(): idx for idx, name in CHAR_OLD_INDEX.items()}
ALIASES = {"dagger": "garnet", "salamander": "amarant"}


def resolve_member(name) -> int:
    """CharacterOldIndex for a member name (case-insensitive; aliases ``dagger``->garnet,
    ``salamander``->amarant). A bare int 0..11 passes through. Raises ``ValueError`` on an unknown name."""
    if isinstance(name, bool):                       # guard: bools are ints in Python, never a valid member
        raise ValueError(f"party member must be a name or 0..11, not {name!r}")
    if isinstance(name, int):
        if name in CHAR_OLD_INDEX:
            return name
        raise ValueError(f"party member index {name} out of range (0..11)")
    key = ALIASES.get(str(name).lower().strip(), str(name).lower().strip())
    if key not in NAME_TO_INDEX:
        raise ValueError(f"unknown party member {name!r} -- choose from "
                         f"{', '.join(CHAR_OLD_INDEX[i] for i in sorted(CHAR_OLD_INDEX))} "
                         f"(aliases: dagger, salamander)")
    return NAME_TO_INDEX[key]


def add_member(char_id: int) -> bytes:
    """``partyadd(char_id)`` -> ``05 C5 93 7D <id:i16> 6D 2C 7F`` -- the in-game-proven JOIN form (push the
    MAP scratch result var, push the CharacterOldIndex const, apply B_PARTYADD, assign the result, end)."""
    return (bytes([_region.EXPR_OP, _region.MAP_BOOL, PARTY_SCRATCH, _region.T_CONST])
            + _region._i16(int(char_id)) + bytes([B_PARTYADD, _region.T_ASSIGN, _region.T_END]))


def remove_member(char_id: int) -> bytes:
    """``RemoveParty(char_id)`` -> ``DD 00 <id>`` (statement op ``0xDD``, one literal byte arg)."""
    return opcodes.encode(REMOVE_PARTY, int(char_id))


def party_body(adds=(), removes=()) -> bytes:
    """The Main_Init party sequence (bare bytecode, prepended into Main_Init). Returns ``b""`` when empty
    (so a field with no ``[party]`` stays byte-identical). Removes run first (free a slot), then adds."""
    out = b""
    for cid in removes:
        out += remove_member(int(cid))
    for cid in adds:
        out += add_member(int(cid))
    return out


def inject_party(eb, adds=(), removes=()) -> bytes:
    """Prepend the party sequence to **Main_Init** (entry 0, tag 0). :func:`edit.insert_in_function` fixes the
    entry/func tables; an offset-0 prepend is ALWAYS safe -- even on the ~11% of fields whose Main_Init opens
    with a 0x06 scenario jump table (the engine is IP-relative, so the table shifts wholesale). No adds/removes
    -> the input bytes unchanged (byte-identical to a field with no ``[party]``). Accepts bytes or an
    :class:`EbScript`."""
    data = bytes(eb) if isinstance(eb, (bytes, bytearray)) else eb.to_bytes()
    body = party_body(adds, removes)
    if not body:
        return data
    return edit.insert_in_function(data, 0, 0, 0, body)


def field_resets_party(eb) -> bool:
    """True if the field rebuilds the party roster with ``SetPartyReserve`` (``0xB4``) anywhere that runs at
    field load -- which executes AFTER a prepended ``[party]`` op and can override it. Scans every non-empty
    entry's Init (tag 0) and main loop (tag 1), not just Main_Init: real party-reset logic usually lives in an
    object Init or entry-0 tag-1 (only 2 of 111 reset fields keep it in entry-0/tag-0). The reset can be partial
    or scenario-gated, so this drives an advisory warning, not an error."""
    from ..eb import EbScript
    s = eb if hasattr(eb, "entries") else EbScript.from_bytes(bytes(eb))
    for e in s.entries:
        if e.empty:
            continue
        for f in e.funcs:
            if f.tag not in (0, 1):
                continue
            for ins in s.instrs(f):
                if ins.op == SET_PARTY_RESERVE:
                    return True
    return False
