"""``logic-map`` -- a read-only, legible VIEW of a field's WHOLE event script (``.eb``).

A ``--verbatim`` fork ships the donor's whole compiled ``.eb`` (entry-0 + every object + every gateway +
every shared subroutine), so the declarative ``[[npc]]``/``[[gateway]]`` model is empty -- the content is
raw bytecode (docs/FORK_FIDELITY.md, CLAUDE.md section 8 #14). You can't EXTRACT an NPC's talk handler into a
portable block (it RunScripts into Main_Init shared helpers, drives siblings, puppeteers the player -- proven
0-of-55 tractable). But you CAN make the entanglement *legible*: this module aggregates the scanners the kit
already has into ONE per-field graph --

  * NODES = every ``(entry, function/tag)`` (the byte-exact skeleton from :mod:`ff9mapkit.eb.model`),
    classified by role (Main_Init / a player sequence / an NPC talk handler / a gateway region / a shared
    routine / set-dressing);
  * EDGES = the resolved call graph -- every ``RunScript[Sync|Async](uid, tag)`` resolved to the entry it
    dispatches into via :func:`ff9mapkit.eventscan.resolve_uid` (the one ``GetObjUID`` convention), plus
    ``Field()``/``WorldMap()`` warps and ``StartSeq`` launches;
  * per-node SIDE EFFECTS -- the dialogue lines (``Window*`` txids), item/gil/shop grants, and GLOB story-flag
    reads/writes each routine performs.

It is **read-only and derived** -- the inverse of nothing; it never edits or regenerates the ``.eb``. It is
the data behind Phase 0 of the field-logic-map plan: the foundation the GUI surfaces (so a verbatim fork's
empty tree fills with its real, inspectable content) and a future in-place edit layer keys off.

THE FIDELITY CEILING (honest, permanent): an operand chosen at runtime (an expression-computed uid / Field id
/ item / flag) or a ``REPLY*`` dynamic-caller (``0x16/0x18/0x1A``) cannot be resolved offline -- those are
MARKED in ``unresolved`` but not drawn as edges. The map is high-fidelity-WITH-HOLES, not exhaustive.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field as _dc_field

from .eb.model import EbScript

# --- opcode constants (the side-effect + edge surface) ----------------------------------------------
WINDOW_OPS = {0x1F: 2, 0x20: 2, 0x95: 3, 0x96: 3}   # WindowSync/Async[Ex] -> txid arg index (dialogue.WINDOW_OPS)
ADD_ITEM_OP = 0x48          # AddItem(item_id, count)
REMOVE_ITEM_OP = 0x49       # RemoveItem(item_id, count)
ADD_GIL_OP = 0xCE           # AddGil(amount)
REMOVE_GIL_OP = 0xCF        # RemoveGil(amount)
MENU_OP = 0x75              # Menu(menu_id, sub_id); 2 = shop, 4 = save, 1 = name, 5 = chocograph
SHOP_MENU_ID = 2
SAVE_MENU_ID = 4
FIELD_OP = 0x2B            # Field(dest) -- a field-to-field warp
WORLDMAP_OP = 0xB6         # WorldMap(loc) -- leave to the overworld (loc = a LOCATION id, not a field)
RUNSCRIPT_OPS = (0x10, 0x12, 0x14)        # RunScript[Async|Sync](level, uid, tag)
RUNSCRIPT_NAMES = {0x10: "RunScriptAsync", 0x12: "RunScript", 0x14: "RunScriptSync"}
REPLY_OPS = (0x16, 0x18, 0x1A)            # Reply[Async|Sync] -- dispatch to the DYNAMIC caller (unresolvable)
STARTSEQ_OP = 0x43         # RunSharedScript / STARTSEQ(entry) -- launch a concurrent Seq by ENTRY index
EXPR_STMT_OP = 0x05        # an expression statement (flag reads/writes ride here)
INIT_OBJECT_OP = 0x09      # InitObject(slot, arg) in Main_Init -- spawns/activates an object entry
DEFINE_PC_OP = 0x2C        # DefinePlayerCharacter

# GLOB story-flag expression tokens (shared with eventscan's raw-byte scanners) -----------------------
from .eventscan import (_glob_var_token, _PUSH_CONST16, _T_ASSIGN, _T_OR_ASSIGN,  # noqa: E402
                        _T_NOT, _T_END, _JMP_FALSE, _JMP_TRUE)


# --- data model -------------------------------------------------------------------------------------
@dataclass
class Call:
    """A resolved (or unresolvable) dispatch edge out of a routine."""
    op: str                       # RunScript / RunScriptSync / RunScriptAsync / StartSeq
    uid: int | None
    tag: int | None
    target_kind: str              # self | player | party | main | object | seq | unknown
    targets: list                 # candidate entry index(es) it dispatches into ([] = unresolved offline)
    off: int
    label: str = ""


@dataclass
class Node:
    """One ``(entry, function/tag)`` with everything it does, attributed per-routine."""
    entry: int
    tag: int
    kind: str                     # main_init / shared_routine / player_seq / npc_talk / object_loop / ...
    abs_start: int
    abs_end: int
    says: list = _dc_field(default_factory=list)        # [{txid, text}]
    gives: list = _dc_field(default_factory=list)        # [{kind, ...}] item/gil/shop/save/menu/remove_*
    flags_set: list = _dc_field(default_factory=list)    # [{index, mode}] mode = set | or
    flags_read: list = _dc_field(default_factory=list)   # [{index, require_set}]
    warps: list = _dc_field(default_factory=list)         # [{op, to}] Field / WorldMap
    calls: list = _dc_field(default_factory=list)         # [Call]
    branches: list = _dc_field(default_factory=list)      # [{op, base, edges:[{value, target, is_default}]}] switch tables
    unresolved: list = _dc_field(default_factory=list)    # [{op, reason, off}] runtime-computed / dynamic

    @property
    def empty(self) -> bool:
        return not (self.says or self.gives or self.flags_set or self.flags_read
                    or self.warps or self.calls or self.branches or self.unresolved)


@dataclass
class EntryInfo:
    """One entry-table slot, classified."""
    index: int
    role: str                     # main | player | npc | object | gateway | logic | empty
    model_id: int | None = None
    model_name: str | None = None
    talkable: bool = False
    spawns: int = 0               # how many times Main_Init InitObject()s this entry (0 = not spawned)
    tags: list = _dc_field(default_factory=list)


@dataclass
class LogicMap:
    field_id: int = 0
    fbg_name: str = ""
    event_name: str = ""
    has_text: bool = False
    sha256: str = ""
    entries: list = _dc_field(default_factory=list)      # EntryInfo
    nodes: list = _dc_field(default_factory=list)        # Node


# --- per-routine attribution helpers ----------------------------------------------------------------
def _line_text(entries, txid, width: int = 60):
    """A readable one-line rendering of dialogue txid (or None if no .mes / not found)."""
    if txid is None or not entries:
        return None
    e = entries.get(int(txid))
    if e is None:
        return None
    from .dialogue import strip_tags
    s = strip_tags(e.text).replace("\n", " / ").strip()
    s = " ".join(s.split())
    return (s[:width] + "...") if len(s) > width else (s or "(blank line)")


def _flag_write_at(d: bytes, off: int):
    """If the 0x05 expression at ``off`` is a GLOB flag WRITE (``05 <glob> 7D <i16> 2C|3F 7F``), return
    ``(idx, mode)`` (mode = 'set'|'or'); else None. Mirrors :func:`eventscan.scan_flags_set` per-instr."""
    tok = _glob_var_token(d, off + 1)
    if tok is None:
        return None
    idx, vlen = tok
    p = off + 1 + vlen
    if p + 4 < len(d) and d[p] == _PUSH_CONST16 and d[p + 3] in (_T_ASSIGN, _T_OR_ASSIGN) and d[p + 4] == _T_END:
        return (idx, "set" if d[p + 3] == _T_ASSIGN else "or")
    return None


def _flag_read_at(d: bytes, off: int):
    """If the 0x05 expression at ``off`` is a GLOB flag READ driving a conditional jump, return
    ``(idx, require_set)``; else None. Mirrors :func:`eventscan.scan_required_flags` per-instr."""
    tok = _glob_var_token(d, off + 1)
    if tok is None:
        return None
    idx, vlen = tok
    p = off + 1 + vlen
    negated = p < len(d) and d[p] == _T_NOT
    if negated:
        p += 1
    if p + 1 >= len(d) or d[p] != _T_END:
        return None
    jmp = d[p + 1]
    if jmp not in (_JMP_FALSE, _JMP_TRUE):
        return None
    require_set = (jmp == _JMP_TRUE and not negated) or (jmp == _JMP_FALSE and negated)
    return (idx, require_set)


def _func_kind(role: str, tag: int) -> str:
    """A readable kind for a (role, tag) -- the engine's func-tag conventions."""
    if role == "main":
        return {0: "main_init", 10: "main_reinit"}.get(tag, "shared_routine")
    if role == "player":
        return {0: "player_init", 1: "player_loop"}.get(tag, "player_seq")
    if role == "gateway":
        return {2: "gateway_tread", 3: "gateway_press", 10: "gateway_reinit"}.get(tag, "gateway_routine")
    if role in ("npc", "object"):
        return {0: "object_init", 1: "object_loop", 2: "object_tread", 3: "npc_talk",
                10: "object_reinit"}.get(tag, "object_routine")
    return {0: "init", 2: "tread", 3: "press", 10: "reinit"}.get(tag, "routine")


# --- the builder ------------------------------------------------------------------------------------
def build_logic_map(eb_bytes, *, entries=None, field_id: int = 0, fbg_name: str = "",
                    event_name: str = "") -> LogicMap:
    """Build a :class:`LogicMap` from a field's ``.eb`` bytes (pure; ``entries`` = a parsed ``.mes``
    ``{txid: MesEntry}`` to enrich dialogue with real text -- omit for the structure-only view)."""
    from . import eventscan
    from . import forkreport as FR
    from ._modeldb import MODELS

    lm = LogicMap(field_id=field_id, fbg_name=fbg_name, event_name=event_name, has_text=bool(entries))
    if not eb_bytes:
        return lm
    data = bytes(eb_bytes)
    lm.sha256 = hashlib.sha256(data).hexdigest()
    eb = EbScript.from_bytes(data)

    player_entries = eventscan.resolve_player_entries(eb)
    gateway_entries = {g["entry_idx"] for g in eventscan.scan_gateway_entries(data)}

    # count Main_Init InitObject() spawns per entry (0 = the entry is defined but never activated)
    spawns: dict = {}
    e0 = next((e for e in eb.entries if not e.empty and e.index == 0), None)
    f0 = e0.func_by_tag(0) if e0 else None
    if f0 is not None:
        for ins in eb.instrs(f0):
            if ins.op == INIT_OBJECT_OP and ins.args and isinstance(ins.args[0], int):
                spawns[int(ins.args[0])] = spawns.get(int(ins.args[0]), 0) + 1

    for e in eb.entries:
        if e.empty:
            lm.entries.append(EntryInfo(e.index, "empty"))
            continue
        rd = eventscan._read_object_init(eb, e.func_by_tag(0)) if e.func_by_tag(0) else {}
        model_id = rd.get("model")
        model_name = MODELS.get(model_id) if model_id is not None else None
        talkable = e.func_by_tag(3) is not None
        if e.index == 0:
            role = "main"
        elif e.index in player_entries or rd.get("player"):
            role = "player"
        elif e.index in gateway_entries:
            role = "gateway"
        elif model_id is not None:
            role = "npc" if talkable else "object"
        else:
            role = "logic"
        lm.entries.append(EntryInfo(e.index, role, model_id, model_name, talkable,
                                    spawns.get(e.index, 0), [f.tag for f in e.funcs]))

        for f in e.funcs:
            node = Node(e.index, f.tag, _func_kind(role, f.tag), f.abs_start, f.abs_end)
            for ins in eb.instrs(f):
                op = ins.op
                if op in WINDOW_OPS:
                    txid = ins.imm(WINDOW_OPS[op])
                    if txid is None:
                        node.unresolved.append({"op": ins.name, "reason": "text chosen at runtime", "off": ins.off})
                    else:
                        node.says.append({"txid": int(txid), "text": _line_text(entries, txid)})
                elif op == ADD_ITEM_OP:
                    iid = ins.imm(0)
                    if iid is None:
                        node.unresolved.append({"op": ins.name, "reason": "item chosen at runtime", "off": ins.off})
                    elif iid != FR.NO_ITEM and not FR.item_inert(iid):   # skip the engine no-op grants (as scan_item_ops)
                        node.gives.append({"kind": "item", "id": int(iid), "count": ins.imm(1),
                                           "label": FR.item_label(iid)})
                elif op == REMOVE_ITEM_OP:
                    node.gives.append({"kind": "remove_item", "id": ins.imm(0), "count": ins.imm(1)})
                elif op == ADD_GIL_OP:
                    node.gives.append({"kind": "gil", "amount": ins.imm(0)})
                elif op == REMOVE_GIL_OP:
                    node.gives.append({"kind": "remove_gil", "amount": ins.imm(0)})
                elif op == MENU_OP:
                    mid = ins.imm(0)
                    if mid == SHOP_MENU_ID:
                        node.gives.append({"kind": "shop", "id": ins.imm(1)})
                    elif mid == SAVE_MENU_ID:
                        node.gives.append({"kind": "save_menu"})
                    elif mid is not None:
                        node.gives.append({"kind": "menu", "id": int(mid)})
                elif op == FIELD_OP:
                    to = ins.imm(0)
                    if to is None:
                        node.unresolved.append({"op": ins.name, "reason": "warp target computed", "off": ins.off})
                    else:
                        node.warps.append({"op": "Field", "to": int(to)})
                elif op == WORLDMAP_OP:
                    loc = ins.imm(0)
                    node.warps.append({"op": "WorldMap", "to": int(loc) if loc is not None else None})
                elif op in RUNSCRIPT_OPS:
                    uid, t = ins.imm(1), ins.imm(2)
                    if uid is None or t is None:
                        node.unresolved.append({"op": ins.name, "reason": "call target computed", "off": ins.off})
                    else:
                        kind, targets = eventscan.resolve_uid(uid, e.index, player_entries, eb.entry_count)
                        node.calls.append(Call(RUNSCRIPT_NAMES.get(op, ins.name), int(uid), int(t),
                                               kind, targets, ins.off, _call_label(kind, uid, t)))
                elif op == STARTSEQ_OP:
                    slot = ins.imm(0)
                    if slot is None:
                        node.unresolved.append({"op": ins.name, "reason": "seq target computed", "off": ins.off})
                    else:
                        node.calls.append(Call("StartSeq", None, None, "seq", [int(slot)], ins.off,
                                               f"starts concurrent seq (entry #{slot})"))
                elif op in REPLY_OPS:
                    node.unresolved.append({"op": ins.name, "reason": "dispatches to the dynamic caller",
                                            "off": ins.off})
                elif ins.is_switch:
                    sw = ins.switch()
                    if sw is None:
                        node.unresolved.append({"op": ins.name, "reason": "switch operands computed", "off": ins.off})
                    else:
                        node.branches.append({"op": ins.name, "base": sw.base,
                                              "edges": [{"value": e.value, "target": e.target,
                                                         "is_default": e.is_default} for e in sw.edges]})
                elif op == EXPR_STMT_OP:
                    w = _flag_write_at(data, ins.off)
                    if w is not None:
                        node.flags_set.append({"index": w[0], "mode": w[1]})
                    else:
                        r = _flag_read_at(data, ins.off)
                        if r is not None:
                            node.flags_read.append({"index": r[0], "require_set": r[1]})
            lm.nodes.append(node)
    return lm


def _call_label(kind: str, uid, tag) -> str:
    return {
        "self": f"runs its own routine #{tag}",
        "player": f"directs the player (sequence #{tag})",
        "party": f"calls a party member (routine #{tag})",
        "main": f"runs shared field logic (Main_Init routine #{tag})",
        "object": f"drives object #{uid} (routine #{tag})",
    }.get(kind, f"calls uid {uid} (routine #{tag})")


# --- id -> bytes loader (the install-backed entry point) --------------------------------------------
def logic_map(field_id: int, *, game=None, bundle=None, lang: str = "us") -> LogicMap:
    """Load a real field's ``.eb`` (+ ``.mes`` for dialogue text) and build its :class:`LogicMap`.
    Read-only; degrades to ``<line N>`` placeholders without an install. Mirrors ``forkreport.explain``."""
    from .extract import EventBundle, ID_TO_FBG, ID_TO_EVT
    b = bundle or EventBundle(game)
    data = b.eb_for_id(field_id)
    entries = None
    try:
        from . import dialogue as _d
        mes = _d.extract_field_mes(str(field_id), lang=lang, game=game)
        if mes:
            entries = _d.parse_mes(mes)
    except Exception:
        entries = None
    return build_logic_map(data, entries=entries, field_id=field_id,
                           fbg_name=ID_TO_FBG.get(field_id, ""), event_name=ID_TO_EVT.get(field_id, ""))


# --- serialization ----------------------------------------------------------------------------------
def to_dict(lm: LogicMap) -> dict:
    """A JSON-serializable dict of the map (the generated read-only VIEW)."""
    return {
        "field_id": lm.field_id, "fbg_name": lm.fbg_name, "event_name": lm.event_name,
        "has_text": lm.has_text, "generated_from_sha256": lm.sha256,
        "entries": [vars(e) for e in lm.entries],
        "nodes": [{**{k: v for k, v in vars(n).items() if k != "calls"},
                   "calls": [vars(c) for c in n.calls]} for n in lm.nodes],
    }


# --- readable rendering -----------------------------------------------------------------------------
_ROLE_GLYPH = {"main": "*", "player": "@", "npc": "o", "object": ".", "gateway": ">", "logic": "-"}


def _fmt_node_lines(n: Node, indent: str = "        ") -> list:
    out = []
    for s in n.says:
        t = s["text"] if s["text"] else f"<line {s['txid']}>"
        out.append(f'{indent}"{t}"')
    for g in n.gives:
        if g["kind"] == "item":
            out.append(f"{indent}gives {g['label']}" + (f" x{g['count']}" if g.get("count") not in (None, 1) else ""))
        elif g["kind"] == "gil":
            out.append(f"{indent}gives gil" + (f" ({g['amount']})" if g.get("amount") is not None else ""))
        elif g["kind"] == "shop":
            out.append(f"{indent}opens shop #{g.get('id')}")
        elif g["kind"] == "save_menu":
            out.append(f"{indent}opens the save menu")
        elif g["kind"] == "menu":
            out.append(f"{indent}opens menu #{g.get('id')}")
        elif g["kind"] == "remove_item":
            out.append(f"{indent}takes item #{g.get('id')}")
        elif g["kind"] == "remove_gil":
            out.append(f"{indent}takes gil")
    for fr in n.flags_read:
        out.append(f"{indent}reads flag {fr['index']} (needs {'set' if fr['require_set'] else 'clear'})")
    for fs in n.flags_set:
        out.append(f"{indent}{'sets' if fs['mode'] == 'set' else 'or-sets'} flag {fs['index']}")
    for w in n.warps:
        out.append(f"{indent}{w['op']}({w.get('to')})")
    for c in n.calls:
        tgt = f" -> entry {c.targets}" if c.targets else ""
        out.append(f"{indent}-> {c.label}{tgt}")
    for b in n.branches:
        ncases = sum(1 for e in b["edges"] if not e["is_default"])
        arms = [("default" if e["is_default"] else str(e["value"])) + f"->@{e['target']}" for e in b["edges"]]
        shown = ", ".join(arms[:6]) + (f", ... (+{len(arms) - 6} more)" if len(arms) > 6 else "")
        out.append(f"{indent}switch ({ncases} cases): {shown}")
    for u in n.unresolved:
        out.append(f"{indent}? {u['op']}: {u['reason']}")
    return out


def node_summary(n: Node) -> str:
    """A terse ONE-LINE 'what this routine does' from the per-routine attribution (calls / dialogue / rewards /
    flags / warps / branches) -- context for the GUI edit panel + tooling. ``''`` for an empty routine. This is
    a SUMMARY, not the full transcript (:func:`_fmt_node_lines` lists each item)."""
    parts = []
    if n.calls:
        tags = sorted({c.tag for c in n.calls if c.tag is not None})
        parts.append(f"runs tag {tags[0]}" if (len(n.calls) == 1 and len(tags) == 1)
                     else f"calls {len(n.calls)} routines")
    if n.says:
        parts.append(f"says {len(n.says)} line" + ("s" if len(n.says) != 1 else ""))
    gkinds = [g["kind"] for g in n.gives]
    reward = sum(1 for k in gkinds if k in ("item", "gil"))
    if reward:
        parts.append(f"gives {reward} reward" + ("s" if reward != 1 else ""))
    for kind, phrase in (("shop", "opens a shop"), ("save_menu", "opens the save menu"),
                         ("menu", "opens a menu"), ("remove_item", "takes an item"), ("remove_gil", "takes gil")):
        c = gkinds.count(kind)
        if c:
            parts.append(phrase + (f" ×{c}" if c > 1 else ""))
    if n.flags_read:
        parts.append(f"reads flag {n.flags_read[0]['index']}" if len(n.flags_read) == 1
                     else f"reads {len(n.flags_read)} flags")
    if n.flags_set:
        parts.append(f"sets flag {n.flags_set[0]['index']}" if len(n.flags_set) == 1
                     else f"sets {len(n.flags_set)} flags")
    if n.warps:
        parts.append(f"{len(n.warps)} warp" + ("s" if len(n.warps) != 1 else ""))
    if n.branches:
        parts.append(f"{len(n.branches)} switch" + ("es" if len(n.branches) != 1 else ""))
    if n.unresolved:
        parts.append(f"{len(n.unresolved)} runtime-computed")
    return " · ".join(parts)


def node_report(n: Node) -> list:
    """A FRIENDLY, human-readable per-routine transcript (for the GUI 'What this routine does' block). Less
    cryptic than :func:`_fmt_node_lines`: dialogue shows its text, flag READS read as run-conditions, flag
    WRITES say 'sets story flag N', warps say 'warps to field N' / 'exits to the world map', and switch arms
    show their CASE VALUES (the scenario / menu-row numbers) instead of raw byte offsets. The inherent
    crypticness that remains -- raw story-flag indices + routine #tags -- has no friendlier source (FF9 story
    flags + function tags are unnamed). Empty list for an empty routine."""
    out = []
    for s in n.says:
        out.append(f'Says: "{s["text"] or ("line " + str(s["txid"]))}"')
    for g in n.gives:
        k = g["kind"]
        if k == "item":
            out.append("Gives the player " + g["label"]
                       + (f" ×{g['count']}" if g.get("count") not in (None, 1) else ""))
        elif k == "gil":
            out.append(f"Gives {g['amount']} gil" if g.get("amount") is not None else "Gives gil")
        elif k == "shop":
            out.append("Opens a shop")
        elif k == "save_menu":
            out.append("Opens the save-point menu")
        elif k == "menu":
            out.append(f"Opens a menu (#{g.get('id')})")
        elif k == "remove_item":
            out.append(f"Takes an item (#{g.get('id')})")
        elif k == "remove_gil":
            out.append("Takes gil")
    for fr in n.flags_read:
        out.append(f"Runs only if story flag {fr['index']} is " + ("SET" if fr["require_set"] else "CLEAR"))
    for fs in n.flags_set:
        out.append(("Sets" if fs["mode"] == "set" else "Sets (OR into)") + f" story flag {fs['index']}")
    for w in n.warps:
        op = str(w["op"])
        if op.lower().startswith("field"):
            out.append(f"Warps to field {w.get('to')}")
        elif "world" in op.lower():
            out.append("Exits to the world map")
        else:
            out.append(f"{op}({w.get('to')})")
    for c in n.calls:
        lbl = c.label or f"calls routine #{c.tag}"
        tgt = f" [→ entry {', '.join(str(t) for t in c.targets)}]" if c.targets else ""
        out.append(lbl[:1].upper() + lbl[1:] + tgt)
    for b in n.branches:
        vals = [str(e["value"]) for e in b["edges"] if not e["is_default"]]
        if vals:
            shown = ", ".join(vals[:8]) + (f", +{len(vals) - 8} more" if len(vals) > 8 else "")
            out.append(f"Branches on a value → cases {shown} (else a default path)")
        else:
            out.append("Branches (a default path only)")
    for u in n.unresolved:
        out.append(f"Calls a routine chosen at runtime — {u['reason']}")
    return out


def node_hint(n: Node) -> str:
    """A SHORT, high-confidence tree-label suffix -- emitted ONLY when the routine has a SINGLE kind of action
    (so the hint can't mislead). A mixed routine returns ``''`` and stays plain (its detail is in the panel
    summary / :func:`_fmt_node_lines`)."""
    cats = (bool(n.calls), bool(n.says), bool(n.gives), bool(n.warps), bool(n.flags_set), bool(n.branches))
    if sum(cats) != 1:
        return ""
    if n.calls:
        tags = sorted({c.tag for c in n.calls if c.tag is not None})
        return f" → tag {tags[0]}" if (len(n.calls) == 1 and len(tags) == 1) else f" → {len(n.calls)} calls"
    if n.warps:
        return " → warp"
    if n.says:
        return " · dialogue"
    if n.gives:
        return " · reward"
    if n.flags_set:
        return " · sets flag"
    return " · switch"                                        # the only remaining single category (branches)


def format_logic_map(lm: LogicMap) -> str:
    """Render a :class:`LogicMap` as a readable per-entry transcript of the whole script."""
    head = lm.fbg_name or f"field {lm.field_id}"
    suffix = f"  (field {lm.field_id}{', ' + lm.event_name if lm.event_name else ''})"
    out = [f"logic-map: {head}{suffix}", ""]
    used = [e for e in lm.entries if e.role != "empty"]
    out.append(f"  {len(used)} entries, {len(lm.nodes)} routines"
               f"{'' if lm.has_text else '   (no install/.mes -> dialogue as <line N>)'}")
    out.append("")
    by_entry: dict = {}
    for n in lm.nodes:
        by_entry.setdefault(n.entry, []).append(n)
    for e in lm.entries:
        if e.role == "empty":
            continue
        glyph = _ROLE_GLYPH.get(e.role, " ")
        model = f"  {e.model_name or ('model ' + str(e.model_id))}" if e.model_id is not None else ""
        spawn = "" if e.role in ("main", "player") or e.spawns else "  (defined, not spawned)"
        out.append(f"  {glyph} entry {e.index}: {e.role}{model}{spawn}")
        for n in by_entry.get(e.index, []):
            lines = _fmt_node_lines(n)
            if not lines:
                continue
            out.append(f"      [{n.kind} / tag {n.tag}]")
            out.extend(lines)
        out.append("")
    return "\n".join(out).rstrip()
