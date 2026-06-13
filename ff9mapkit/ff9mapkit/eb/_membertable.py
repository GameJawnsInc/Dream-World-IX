"""Battle-AI ``B_MEMBER(N)`` selector -> field-name table (the read/write members of a battle unit).

In a battle ``.eb`` AI expression, ``B_SYSLIST[u] B_MEMBER(N)`` reads member ``N`` of battle unit ``u``
(``B_SYSLIST[1]`` = the acting unit / SELF, ``B_SYSLIST[0]`` = the target). ``N`` is NOT a byte offset -- it is a
SWITCH-CASE selector in Memoria's ``btl_scrp.GetCharacterData(BTL_DATA, id)`` (and the symmetric
``SetCharacterData``, so ``B_MEMBER(N) <expr> B_LET_A`` WRITES it). This table maps the selectors to readable
names so the disassembler can annotate ``B_MEMBER(36)`` as ``cur.hp`` and an author can write ``B_MEMBER(cur.hp)``.

Provenance-clean: only the case numbers + field NAMES (transcribed from the open-source ``btl_scrp.cs`` switch),
no SE bytes. Distinct from the op_binary ``B_CURHP``/``B_MAXHP`` tokens (``_exprtable``), which read a PARTY slot
via ``GetPlayer`` -- NOT the acting unit's own battle HP. See memory ``project-ff9-battle-ai-members``.
"""
from __future__ import annotations

# selector (GetCharacterData case id) -> canonical name. Only the READABLE cases are listed (a few selectors are
# write-only -- e.g. 55/56 model-scale -- and return a default when read; omitted to avoid implying a read).
MEMBER_NAMES: dict[int, str] = {
    35: "max.hp", 36: "cur.hp", 37: "max.mp", 38: "cur.mp", 39: "max.at", 40: "cur.at", 41: "level",
    42: "status.invalid.hi", 43: "status.invalid.lo", 44: "status.permanent.hi", 45: "status.permanent.lo",
    46: "status.cur.hi", 47: "status.cur.lo",
    48: "elem.invalid", 49: "elem.absorb", 50: "elem.half", 51: "elem.weak",
    52: "target", 53: "disappear", 57: "geo_id", 58: "mesh", 64: "row", 65: "line_no",
    72: "str", 73: "mgc", 74: "phys_def", 75: "phys_evade", 76: "mag_def", 77: "mag_evade",
    112: "motion", 114: "cur_attack",
    140: "pos.x", 141: "pos.ny", 142: "pos.z", 146: "exp", 147: "gil", 148: "trance", 149: "t_gauge",
}

_NAME_TO_SELECTOR: dict[str, int] = {n: s for s, n in MEMBER_NAMES.items()}


def member_name(selector: int) -> str | None:
    """The field name for a ``B_MEMBER`` selector (e.g. 36 -> ``cur.hp``), or None if not a known readable member."""
    return MEMBER_NAMES.get(selector)


def member_selector(name: str) -> int | None:
    """The ``B_MEMBER`` selector for a field name (e.g. ``cur.hp`` -> 36), or None if the name is unknown."""
    return _NAME_TO_SELECTOR.get(name)
