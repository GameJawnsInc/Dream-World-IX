"""Chocobo Hot & Cold -- the declarative dig-prize / timer lane on a verbatim forest fork.

FF9's minigame is ~100% field ``.eb``: each forest (2950 Chocobo's Forest / 2951 Lagoon / 2952 Air
Garden) rolls a dig's prize by assigning a literal to the runtime prize var -- 35 slot-shaped
``{opDE(20) op7D(v) op2C op7F}`` assigns across the RNG tiers of ONE function (2950: entry 8 tag 41)
-- records it in the per-session find-history (``opDD(56..70)``), and BOTH the end-of-game award
(2950: entry 0 tag 24 ``AddItem({opDE(4)},1)`` @5209) and the "You found X!" popups read that value
back. Editing a slot literal AT ITS SOURCE therefore changes the give AND the popup name together --
the 2026-06-13 byte-patch spike's text-mismatch bug is structurally impossible on this lane.

This module is a THIN resolver (no byte-patching of its own): it SCANS the pool + timer from the
fork's composed bytes, EXPORTS them as an editable ``[chocobo]`` block, and RESOLVES the authored
block into ``[[logic_edit]] kind="expr_literal"`` dicts -- apply / old-guards / eblint stay owned by
:mod:`ff9mapkit.logic_edit` and the build's existing verbatim pass.

Value routing (engine-verified): ``v < 1000`` = item id (awarded at game end via the find-history);
``1000 <= v < 30000`` = gil, amount ``v - 1000`` (awarded IMMEDIATELY in the dig handler, ``AddGi``);
``30000`` = the "special" sentinel init (never a slot); ``30001`` = the dig found nothing.
Drop ODDS are the RNG jump tables (variable-length) -- not editable on this lane.

-> project memory: project-ff9-chocobo-hot-cold (offsets + the F6 warp-in recipe).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .. import items as _items
from ..eb import disasm
from ..eb.model import EbScript

GIL_BASE = 1000              # slot value >= 1000 -> gil, amount = value - 1000
GIL_MAX = 28999              # keep authored gil below the 30000+ sentinel band
SPECIAL = 30000              # the pool var's "special" init sentinel -- excluded from the slot list
NOTHING = 30001              # "found nothing"
TIMER_OP = 0x69              # ChangeTimerTime
_MIN_SLOTS = 8               # a pool is only recognized at >= this many slot-shaped assigns
_ASSIGN_RE = re.compile(r"^\{(op[0-9A-F]{2}\(\d+\)) op7D\((\d+),(\d+)\) op2C op7F\}$")
_TIER_RE = re.compile(r"^op[0-9A-F]{2}\(\d+\)$")


class ChocoboError(ValueError):
    """A [chocobo] block that can't be resolved safely (no pool in this field, bad keys, out-of-range
    values) -- fails the build/Check cleanly, never silently mis-patches."""


@dataclass(frozen=True)
class PrizeSlot:
    """One dig-prize slot: a literal assign to the pool var, editable in place."""
    index: int          # flat slot index (byte order) -- the [[chocobo.prize]] `slot` key
    entry: int
    tag: int
    off: int            # abs offset of the op_05 instruction
    payload_off: int    # abs offset of the 2-byte B_CONST payload (the editable literal)
    value: int          # current prize value (item id / 1000+gil / 30001)
    expr: str           # the instruction's exact decoded expression text (the applier's guard)
    nth: "int | None"   # disambiguator among identical-expr hits (None when unique)
    tier: "int | None"  # RNG tier annotation (cosmetic; None when no tier marker var was found)


@dataclass(frozen=True)
class TimerSite:
    """The game timer's seed literal (in-game seconds = seed * difficulty + 1)."""
    entry: int
    tag: int
    off: int
    payload_off: int
    value: int
    expr: str
    nth: "int | None"


@dataclass(frozen=True)
class ChocoboScan:
    """Everything the [chocobo] lane can author in this field's bytes."""
    slots: tuple
    timer: "TimerSite | None"
    pool_var: str       # e.g. "opDE(20)" -- the prize var's decoded token text
    pool_entry: int
    pool_tag: int


def _pure_assigns(eb: EbScript):
    """Yield ``(entry, tag, var_text, ins, value)`` for every ``{var op7D(v) op2C op7F}`` pure-literal
    assign in the script -- the shape both the prize slots and the tier markers use."""
    for e in eb.entries:
        if e.empty:
            continue
        for fn in e.funcs:
            for ins in eb.instrs(fn):
                if ins.op != 0x05 or not ins.arg_is_expr or not ins.arg_is_expr[0]:
                    continue
                m = _ASSIGN_RE.match(ins.args[0])
                if not m:
                    continue
                yield e.index, fn.tag, m.group(1), ins, int(m.group(2)) | (int(m.group(3)) << 8)


def scan(eb_bytes) -> "ChocoboScan | None":
    """Discover the dig-prize pool + the timer seed in *eb_bytes*. Returns ``None`` when the field has
    no recognizable pool (not a Hot & Cold forest). Structure-driven, not offset-driven: the pool is
    the largest single-function family of pure-literal assigns to ONE var that includes gil/sentinel
    (>= ``GIL_BASE``) values -- verified to find (entry 8 tag 41 / 12:38 / 8:46) x 35 slots on the
    real 2950/2951/2952; a [startup]/[[on_entry]] insert or retarget never changes this."""
    eb = EbScript.from_bytes(eb_bytes)
    groups: dict = {}
    for entry, tag, var, ins, val in _pure_assigns(eb):
        groups.setdefault((entry, tag, var), []).append((ins, val))
    pools = {k: rows for k, rows in groups.items()
             if len(rows) >= _MIN_SLOTS and any(v >= GIL_BASE for _, v in rows)}
    if not pools:
        return None
    pool_key = max(pools, key=lambda k: (len(pools[k]), -k[0], -k[1]))
    pool_entry, pool_tag, pool_var = pool_key
    rows = sorted(pools[pool_key], key=lambda r: r[0].off)
    slot_rows = [r for r in rows if r[1] != SPECIAL]          # the editable slots (sentinel inits excluded)
    if not slot_rows:
        return None

    # tier annotation (cosmetic): a marker var in the SAME function whose literal assigns WITHIN the slot
    # region are a strictly DESCENDING run of small values (2950: opD5(53) = 5,4,3,2,1 -- the RNG tier
    # register; an unrelated init of the same var elsewhere in the function is out-of-window).
    lo_w, hi_w = slot_rows[0][0].off - 96, slot_rows[-1][0].off + 1
    tier_marks: list = []
    for (entry, tag, var), mrows in groups.items():
        if (entry, tag) != (pool_entry, pool_tag) or var == pool_var:
            continue
        inwin = sorted(((ins.off, v) for ins, v in mrows if lo_w <= ins.off < hi_w))
        seq = [v for _, v in inwin]
        if len(seq) >= 3 and all(1 <= v <= 9 for v in seq) and all(a > b for a, b in zip(seq, seq[1:])):
            tier_marks = inwin
            break

    def _tier(off: int):
        t = None
        for moff, v in tier_marks:
            if moff < off:
                t = v
        return t

    # nth mirrors the expr_literal applier's hit ordering: consts == value inside instrs matching
    # (op 0x05, expr == text) walked in function byte order. Identical-expr slots are the only hits.
    by_expr: dict = {}
    slots = []
    for ins, _val in slot_rows:
        by_expr.setdefault(ins.args[0], []).append(ins)
    for ins, val in slot_rows:
        peers = by_expr[ins.args[0]]
        consts = disasm.instr_expr_consts(eb.data, ins)
        slots.append(PrizeSlot(index=len(slots), entry=pool_entry, tag=pool_tag, off=ins.off,
                               payload_off=consts[0][0], value=val, expr=ins.args[0],
                               nth=peers.index(ins) if len(peers) > 1 else None, tier=_tier(ins.off)))

    # the timer SEED: the ChangeTimerTime whose expression LEADS with a literal (`{seed * difficulty + 1}`);
    # the +10s find-bonus sites lead with the remaining-time sysvar and are left alone.
    timer = None
    for e in eb.entries:
        if e.empty or timer is not None:
            continue
        for fn in e.funcs:
            for ins in eb.instrs(fn):
                if ins.op != TIMER_OP or not ins.arg_is_expr or not ins.arg_is_expr[0]:
                    continue
                if not ins.args[0].startswith("{op7D("):
                    continue
                consts = [c for c in disasm.instr_expr_consts(eb.data, ins) if c[2] == 0]
                seed_off, seed_val, _ = consts[0]
                same = [c for c in consts if c[1] == seed_val]
                timer = TimerSite(entry=e.index, tag=fn.tag, off=ins.off, payload_off=seed_off,
                                  value=seed_val, expr=ins.args[0],
                                  nth=same.index(consts[0]) if len(same) > 1 else None)
                break
            if timer is not None:
                break
    return ChocoboScan(slots=tuple(slots), timer=timer, pool_var=pool_var,
                       pool_entry=pool_entry, pool_tag=pool_tag)


# ------------------------------------------------------------------ export --
def _slot_value_line(value: int) -> str:
    if value == NOTHING:
        return "nothing = true"
    if value >= GIL_BASE:
        return f"gil = {value - GIL_BASE}"
    nm = _items.name_of(value)
    if nm is not None:
        return f'item = "{nm}"'
    return f"value = {value}   # unnamed item id"


def export_toml(sc: ChocoboScan, *, field_note: str = "") -> str:
    """The editable ``[chocobo]`` block for *sc*, one ``[[chocobo.prize]]`` per slot at its CURRENT
    value -- applying an unedited export is byte-identical (resolve emits zero edits)."""
    lines = [f"# Chocobo Hot & Cold -- dig prize pool + timer{field_note}",
             "# Edit values freely; delete a [[chocobo.prize]] block to keep that slot vanilla.",
             '# A slot is item = "Name" | gil = N | nothing = true | value = N (raw).',
             "# Drop odds / dig spots are not on this lane (RNG jump tables).", ""]
    if sc.timer is not None:
        lines += ["[chocobo.tuning]",
                  f"timer = {sc.timer.value}   # in-game seconds = timer * difficulty + 1", ""]
    for s in sc.slots:
        tier = f" -- tier {s.tier}" if s.tier is not None else ""
        lines += [f"[[chocobo.prize]]   # slot {s.index}{tier}",
                  f"slot = {s.index}",
                  _slot_value_line(s.value), ""]
    return "\n".join(lines)


# ----------------------------------------------------------------- resolve --
def _prize_new_value(p: dict) -> int:
    keys = [k for k in ("item", "gil", "nothing", "value") if k in p]
    if len(keys) != 1:
        raise ChocoboError(f"[[chocobo.prize]] slot {p.get('slot')}: give exactly ONE of item= / gil= / "
                           f"nothing= / value= (got {keys or 'none'})")
    k = keys[0]
    if k == "item":
        try:
            return _items.resolve(p["item"])
        except ValueError as ex:
            raise ChocoboError(f"[[chocobo.prize]] slot {p.get('slot')}: {ex}")
    if k == "gil":
        amt = p["gil"]
        if isinstance(amt, bool) or not isinstance(amt, int) or not (1 <= amt <= GIL_MAX):
            raise ChocoboError(f"[[chocobo.prize]] slot {p.get('slot')}: gil must be an integer "
                               f"1..{GIL_MAX}, got {amt!r}")
        return GIL_BASE + amt
    if k == "nothing":
        if p["nothing"] is not True:
            raise ChocoboError(f"[[chocobo.prize]] slot {p.get('slot')}: `nothing = true` is the only "
                               "accepted form (delete the key to keep the slot)")
        return NOTHING
    v = p["value"]
    if isinstance(v, bool) or not isinstance(v, int) or not (0 <= v <= 0xFFFF):
        raise ChocoboError(f"[[chocobo.prize]] slot {p.get('slot')}: value must be an integer "
                           f"0..65535, got {v!r}")
    return v


def _edit_for(site, new: int) -> dict:
    ed = {"kind": "expr_literal", "entry": site.entry, "tag": site.tag,
          "op": 0x05 if isinstance(site, PrizeSlot) else TIMER_OP,
          "expr": site.expr, "old": site.value, "new": new}
    if site.nth is not None:
        ed["nth"] = site.nth
    return ed


def resolve_edits(eb_bytes, cfg: dict) -> list:
    """Resolve a ``[chocobo]`` block into ``[[logic_edit]] kind="expr_literal"`` dicts against
    *eb_bytes* (call with the SAME composed stream the build's logic_edit pass applies to -- the
    edits self-locate semantically, so upstream length-preserving passes can't invalidate them).
    Unchanged values emit nothing. Raises :class:`ChocoboError` on any unsafe/unknown authoring."""
    if not isinstance(cfg, dict):
        raise ChocoboError("[chocobo] must be a table")
    unknown = set(cfg) - {"tuning", "prize"}
    if unknown:
        raise ChocoboError(f"[chocobo] unknown key(s): {sorted(unknown)} "
                           "(expected [chocobo.tuning] and/or [[chocobo.prize]])")
    prizes = cfg.get("prize") or []
    if not isinstance(prizes, list) or not all(isinstance(p, dict) for p in prizes):
        raise ChocoboError("[[chocobo.prize]] must be an array of tables "
                           "(you likely wrote [chocobo.prize] instead of [[chocobo.prize]])")
    tuning = cfg.get("tuning") or {}
    if not isinstance(tuning, dict):
        raise ChocoboError("[chocobo.tuning] must be a table")
    t_unknown = set(tuning) - {"timer"}
    if t_unknown:
        raise ChocoboError(f"[chocobo.tuning] unknown key(s): {sorted(t_unknown)} (expected timer)")
    if not prizes and "timer" not in tuning:
        return []

    sc = scan(eb_bytes)
    if sc is None:
        raise ChocoboError("no dig-prize pool found in this field's .eb -- [chocobo] only applies to a "
                           "verbatim fork of a Chocobo Hot & Cold forest (2950/2951/2952)")
    edits, seen = [], set()
    for p in prizes:
        p_unknown = set(p) - {"slot", "item", "gil", "nothing", "value", "tier"}
        if p_unknown:
            raise ChocoboError(f"[[chocobo.prize]] unknown key(s): {sorted(p_unknown)}")
        slot_i = p.get("slot")
        if isinstance(slot_i, bool) or not isinstance(slot_i, int) or not (0 <= slot_i < len(sc.slots)):
            raise ChocoboError(f"[[chocobo.prize]] slot must be an integer 0..{len(sc.slots) - 1}, "
                               f"got {slot_i!r}")
        if slot_i in seen:
            raise ChocoboError(f"[[chocobo.prize]] slot {slot_i} authored twice")
        seen.add(slot_i)
        new = _prize_new_value(p)
        s = sc.slots[slot_i]
        if new != s.value:
            edits.append(_edit_for(s, new))
    if "timer" in tuning:
        tv = tuning["timer"]
        if isinstance(tv, bool) or not isinstance(tv, int) or not (1 <= tv <= 0xFFFF):
            raise ChocoboError(f"[chocobo.tuning] timer must be an integer 1..65535 (seconds seed; "
                               f"in-game time = timer * difficulty + 1), got {tv!r}")
        if sc.timer is None:
            raise ChocoboError("[chocobo.tuning] timer: no ChangeTimerTime seed found in this field's .eb")
        if tv != sc.timer.value:
            edits.append(_edit_for(sc.timer, tv))
    return edits


# --------------------------------------------------- GUI authoring helpers --
# Pure dict-in/dict-out edits on a ``[chocobo]`` cfg (never mutate the input), so the Workspace form can
# build a candidate block, dry-run it (resolve_edits + eblint), and only then write it into the field.toml
# -- mirroring logic_edit.upsert_edits. A prize ENTRY is a small dict: {"item": name/id} | {"gil": N} |
# {"nothing": True} | {"value": N} (the slot key is added here). Timer is one int under [chocobo.tuning].
def _clone_cfg(cfg: "dict | None") -> dict:
    import copy
    return copy.deepcopy(cfg) if cfg else {}


def prize_entry(cfg: "dict | None", slot: int) -> "dict | None":
    """The authored ``[[chocobo.prize]]`` entry for ``slot`` in ``cfg`` (its override), or ``None`` when the
    slot is left vanilla."""
    for p in (cfg or {}).get("prize") or []:
        if isinstance(p, dict) and p.get("slot") == slot:
            return p
    return None


def set_prize(cfg: "dict | None", slot: int, entry: "dict | None") -> dict:
    """Return a NEW cfg with ``slot``'s prize set to ``entry`` (item/gil/nothing/value; the ``slot`` key is
    added) or REMOVED when ``entry`` is None (revert to vanilla). Slots stay sorted; an empty ``prize`` list
    drops the key so a fully-reverted block leaves no noise."""
    out = _clone_cfg(cfg)
    prizes = [p for p in (out.get("prize") or [])
              if not (isinstance(p, dict) and p.get("slot") == slot)]
    if entry is not None:
        e = {"slot": int(slot)}
        e.update({k: v for k, v in entry.items() if k != "slot"})
        prizes.append(e)
    prizes.sort(key=lambda p: p.get("slot", 0))
    if prizes:
        out["prize"] = prizes
    else:
        out.pop("prize", None)
    return out


def set_timer(cfg: "dict | None", value: "int | None") -> dict:
    """Return a NEW cfg with ``[chocobo.tuning] timer`` set to ``value`` (or removed when None). An empty
    tuning table drops the key."""
    out = _clone_cfg(cfg)
    tuning = dict(out.get("tuning") or {})
    if value is None:
        tuning.pop("timer", None)
    else:
        tuning["timer"] = int(value)
    if tuning:
        out["tuning"] = tuning
    else:
        out.pop("tuning", None)
    return out


def resolved_value(entry: dict) -> int:
    """The integer prize value an authored entry resolves to (item id / 1000+gil / 30001 / raw). Raises
    :class:`ChocoboError` on a bad entry -- the GUI uses it for the live '→ value' hint + pre-write check."""
    return _prize_new_value(entry if "slot" in entry else {**entry, "slot": 0})
