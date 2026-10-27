"""The PRESS CLOSURE of a field region: what does pressing Confirm inside a region's quad run?

Pure ``.eb`` analysis -- bytes in, verdict out, no install access -- promoted from the study census
``studies/field-coop/guest-traversal/interaction_census.py`` for the co-op guest-traversal table
(``ff9mapkit.guest_traversal``, engine patch s156). It keeps the census's semantics VERBATIM for the one
root kind the table needs, the QUAD root (a region entry's tag-3 function: ``EventCollision.CheckQuadInput``
-> ``TreadQuad(po, 4)`` -> ``Request(obj, 1, 3)``): the opcode -> effect-bucket map, the RPN expression
walker, the per-field model (entry kinds, the uid map with ``uid or sid``, the DefinePlayerCharacter set, the
field-wide var read/write index), the transitive closure walk in instruction order, the tier classifier
(``classify``), the locomotion kind (``loco_kind``) and the root gate. The install-gated pin
(``tests/test_guest_traversal_install.py``) holds this module to the census on every QUAD root of the game,
so the two implementations stay pinned to each other while the census stays the frozen research record.

What the promotion ADDS (the census could not see these; each is a fact the ship filter reads):

* **Edges, by DISPATCH.** Every call the walk follows is recorded with how it dispatches: ``ctrl``
  (``RunScript*(lvl, 250, tag)`` -- the control uid, ONE body at runtime: the control character's), ``fixed_ctrl``
  (a fixed uid that resolves to DefinePlayerCharacter entries), ``seq`` (``RunSharedScript(E)`` -- a new Seq
  running E's tag 0), and the kinds the guest table never ships: ``self`` (uid 255), ``party`` (251-254),
  ``fixed_other``, ``unknown``, ``expr`` (a computed uid or tag), ``sender`` (``RunScriptObject*``) and
  ``spawn`` (``Init*``).
* **Fail-closed flags.** The census walk silently stops at depth > 8 or past its node budget; here that sets
  ``truncated``. An instruction stream or expression that fails to decode sets ``decode_fail``.
* **The PATH-AWARE latch audit** (:func:`latch_consumers`). The census's scratch rule (a reader that ALSO
  writes the closure's var is "another scratch user") is order-blind: field 2702's stone latch Map.Byte[32] is
  read FIRST by four other regions' jump functions, so a guest's press leaves a value they consume. The audit
  walks EVERY function outside the closure (an instance var: only its owner entry's) with its own token-level
  effect walk -- every var token is a READ except the lvalue of a plain ``B_LET``, so ``+=`` / ``++`` and the
  ``x`` of ``x = x + 1`` read -- and a forward MAY-UNCOVERED dataflow over the function's CFG (:func:`latch_access`):
  a read of a bit that some path from the function's start reaches before a plain write covers it makes the
  function READ-FIRST, whatever the byte order says. A read-first function is a consumer unless it is a LOAD-ONCE
  reader (runs only during field init, so it can never see a press's leftover; see :func:`load_once_why`).

The classifier's tier stays the census's order-blind one on purpose: the faithfulness pin compares tiers
exactly, and the ship filter's R11 refusal (``guest_traversal``) is where the path-aware audit acts. The audit's
effect walk is its OWN: ``walk_expr``, ``FieldModel.read_sites``, ``Closure.finish`` and ``classify`` stay the
census's (they drop a read of the very var an instruction writes, which is right for the tier and wrong for a latch).
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass

from ._exprtable import EXPR_OP_NAMES, decode_var
from .cfg import FuncFlow
from .disasm import TERMINATOR_OPS, instr_expr_tokens, jump_target
from .exprsem import OP_SEMANTICS
from .model import EbScript

# ------------------------------------------------------------------ engine constants (census, verbatim)
CONFIRM, SPECIAL, SELECT = 0x20000, 0x80000, 0x1
CIRCLE, CROSS = 0x2000, 0x4000
DIR_BITS = 0x10 | 0x20 | 0x40 | 0x80
HOST_OWNED = (SELECT | 0x1000 | CIRCLE | CROSS | 0x8000 | 0x10000 | CONFIRM | 0x40000 | SPECIAL | 0x1000000)
PLAYER_UID, SELF_UID = 250, 255
PARTY_UIDS = (251, 252, 253, 254)
# the expression-level key reads (NOT opcodes: they are RPN operators inside a SET/JMP expression)
KEY_OPS = {0x4F: "KEYON", 0x58: "KEYOFF", 0x59: "KEY", 0x5A: "KEYON2", 0x5B: "KEYOFF2", 0x5C: "KEY2"}
LET2 = {"B_LET", "B_MULT_LET", "B_DIV_LET", "B_REM_LET", "B_PLUS_LET", "B_MINUS_LET", "B_SHIFT_LEFT_LET",
        "B_SHIFT_RIGHT_LET", "B_AND_LET", "B_XOR_LET", "B_OR_LET"}
INCDEC = {"B_POST_PLUS", "B_POST_MINUS", "B_PRE_PLUS", "B_PRE_MINUS"}
VT_BITS = {0: 1, 1: 1, 2: 24, 3: 24, 4: 8, 5: 8, 6: 16, 7: 16}

CALL_OPS = {0x10: "RunScriptAsync", 0x12: "RunScript", 0x14: "RunScriptSync"}
SENDER_OPS = {0x16: "RunScriptObjectAsync", 0x18: "RunScriptObject", 0x1A: "RunScriptObjectSync"}
SEQ_OP = 0x43                                        # RunSharedScript(entry)
INIT_OPS = {0x07: "InitCode", 0x08: "InitRegion", 0x09: "InitObject"}
DEFINE_PLAYER_OP = 0x2C
BACK_JUMP_OPS = (0x01, 0x02, 0x03)                   # JMP / JMP_IFNOT / JMP_IF (switches only jump forward)
TERMINATE_OP = 0x1C                                  # TerminateEntry(uid): 255 ends ITSELF; any other uid disposes it
RETURN_ENTRY_OP = 0x97                               # ReturnEntryFunctions(uid): DRET -- restarts the target's tag 1
PURE_LET = "B_LET"                                   # the one assignment whose lvalue is not also a READ

# ------------------------------------------------------------------ opcode -> effect bucket (census, verbatim)
B: dict = {}


def _b(name, ops):
    for o in ops:
        B[o] = name


_b("locomotion", [0x1D, 0x23, 0x24, 0x25, 0x26, 0x33, 0x34, 0x35, 0x36, 0x37, 0x3D, 0x3E, 0x3F, 0x40, 0x41, 0x42,
                  0x4B, 0x4C, 0x4D, 0x50, 0x51, 0x52, 0x55, 0x56, 0x6A, 0x7A, 0x7B, 0x86, 0x87, 0x94, 0x98, 0x99,
                  0x9B, 0x9C, 0x9D, 0x9F, 0xA1, 0xA2, 0xA5, 0xA6, 0xA7, 0xA8, 0xAD, 0xBB, 0xBC, 0xBD, 0xBE, 0xBF,
                  0xCC, 0xCD, 0xD4, 0xDC, 0xE2, 0xE8, 0xF0, 0x117, 0x118, 0x119])
_b("cosmetic", [0x39, 0x3A, 0x47, 0x8B, 0x7F, 0x80, 0x81, 0x82, 0x83, 0x84, 0x85, 0x8F, 0x90, 0xEE, 0x93, 0x2F,
                0x3B, 0xD5, 0xD6, 0x68, 0xEF])
_b("camera", [0x1E, 0x6F, 0x70, 0x71, 0x72, 0x73, 0x74, 0x7E, 0x91, 0xC3, 0xA9, 0xEA, 0xB7, 0xB8])
_b("wait_sound", [0x22, 0x89, 0x8A, 0xC5, 0xC6, 0xC7, 0xC8, 0xF6, 0xF7, 0xF8, 0xF9, 0xFA, 0xFB, 0xFC])
_b("fade", [0xEC, 0x6B])
_b("movelock", [0x2D, 0x2E])
_b("control", [0xAA, 0xAB, 0xB9, 0xBA, 0x67])
_b("control_swap", [0x2C])
_b("window", [0x1F, 0x20, 0x21, 0x95, 0x96, 0x54, 0x66, 0x53, 0x8E, 0xEB, 0xE3, 0xD0, 0xB0, 0xB1])
_b("choice", [0x7C])
_b("item_party", [0x48, 0x49, 0xCE, 0xCF, 0xE0, 0xAF, 0x115, 0x116, 0x112, 0x113, 0x114, 0xF1, 0xF2, 0xF3, 0xF4,
                  0xD9, 0xDE, 0xFE, 0xB4, 0xDD, 0xE9, 0xB5, 0x11D, 0x11E])
_b("exit", [0x2B, 0xB6, 0x9E, 0xA0, 0xA4, 0xFD, 0xAC, 0xF5])
_b("battle", [0x2A, 0x8C, 0x3C, 0x57, 0x4A, 0x38, 0xE1, 0xE5, 0xDB, 0x1B])
_b("menu", [0x75, 0xB2, 0xAE])
_b("fmv", [0x28])
_b("ate", [0xD7])
_b("timer", [0x7D, 0x8D, 0x69])
_b("tile_bg", list(range(0x59, 0x66)) + [0x92, 0xC0, 0xC1, 0xC2, 0xC9, 0xCA, 0xE4, 0xE6, 0xE7, 0xED, 0x11C,
                                        0x76, 0x77, 0x78, 0xD8, 0x88, 0x58])
_b("sps", [0xB3, 0xDA])
_b("walkmesh", [0x9A, 0xCB])
_b("bracket", [0x27])   # BGIMASK: the stock talk bracket (127 during, 255 after) -- restored, transient
_b("spawn", [0x07, 0x08, 0x09, 0x1C, 0x29])
_b("call", [0x10, 0x12, 0x14, 0x16, 0x18, 0x1A, 0x43, 0x44, 0x45, 0x97])
_b("flow", [0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x0B, 0x0D])
_b("world", [0xC4])
_b("flex_state", [0x11A, 0x11B])
EX_TARGET_OPS = {0xBF, 0x87, 0xBD, 0xBE, 0xBB, 0xBC, 0xAD, 0x117, 0x118}   # first arg = an object UID

# "allowed anywhere" (local + transient + per-screen): never blocks LOCOMOTION-ONLY / FLAVOR
NEUTRAL = {"camera", "wait_sound", "fade", "movelock", "control", "cosmetic", "flow", "call", "key_dir",
           "key_press", "key_other", "map_private", "local_private", "read_glob", "read_map", "read_item",
           "read_party", "read_rng", "read_choice", "read_other", "unresolved_target_missing", "bracket",
           "map_bracket"}
PERSIST = {"glob_write", "scenario_write", "item_party", "party_add", "member_write", "flex_state", "flex_expr"}
HARD = {"battle", "menu", "fmv", "timer", "control_swap", "world", "ate"}
LATCH = {"map_shared", "local_shared", "walkmesh"}
SCENE = {"spawn", "tile_bg", "sps", "objvar_write", "loco_other", "other"}

# the stock control-macro MAP bits (the talk bracket: 158 = "bracket closed" bookkeeping, set 0 at entry and 1
# at exit by EVERY stock talk; 159/144/156 are its READ-only selectors).
BRACKET_MAP = {(1, 158)}
BRACKET_READ_BITS = {144, 156, 158, 159}   # read by the bracket's own conditions (ignored as a "gate")

#: the census's player-MOVING kinds: a LOCO-ONLY QUAD closure of one of these is a guest-traversal candidate
MOVERS = frozenset({"ladder-navigable", "ladder-auto", "jump", "carry-loop", "walk", "teleport"})

#: the dispatch kinds the guest table ships (every other edge kind refuses the row)
SHIPPABLE_EDGES = frozenset({"ctrl", "fixed_ctrl", "seq"})


def s16(v):
    return v - 65536 if v >= 32768 else v


def var_bits(typ, idx):
    if typ in (0, 1):
        return frozenset([idx])
    n = VT_BITS.get(typ, 8)
    return frozenset(range(idx * 8, idx * 8 + n))


def var_name(src: int, typ: int, idx: int) -> str:
    """``(src, typ, idx)`` -> the disassembler's ``Source.Type[index]`` text (``Map.Byte[32]``)."""
    return decode_var(0xC0 | (typ << 2) | src, idx)


# ------------------------------------------------------------------ expression walker (census, verbatim)
def walk_expr(toks):
    """RPN-walk one decoded token list. Returns dict: writes=[(src,typ,idx)], reads=[(src,typ,idx)],
    keys=[(op, mask|None)], sysv=set, ops=set(names), objw, member_w, partyadd, flex."""
    out = {"writes": [], "reads": [], "keys": [], "sysv": set(), "ops": set(), "objw": False,
           "member_w": False, "partyadd": False, "flex": False, "objr": []}
    st = []
    for (o, v) in toks:
        if o == 0x7F:
            break
        if o == 0xD3:
            fid, argc = v
            for _ in range(min(argc, len(st))):
                st.pop()
            out["flex"] = True
            st.append(("flex",))
            continue
        if o in (0x7D, 0x7E):
            st.append(("const", v))
            continue
        if o >= 0xC0:
            src, typ = o & 3, (o >> 2) & 7
            out["reads"].append((src, typ, v))
            st.append(("var", src, typ, v))
            continue
        if o == 0x78:
            out["objr"].append(v)
            st.append(("obj", v))
            continue
        if o == 0x7A:
            out["sysv"].add(v)
            st.append(("sys", v))
            continue
        if o in (0x79, 0x29, 0x5F):
            st.append(("misc", o, v))
            continue
        name = EXPR_OP_NAMES.get(o, f"op{o:02X}")
        out["ops"].add(name)
        ar, eff = OP_SEMANTICS.get(name, (0, "read"))
        popped = []
        for _ in range(ar):
            popped.append(st.pop() if st else None)
        popped.reverse()
        if name in LET2 or name in INCDEC:
            lv = popped[0] if popped else None
            if lv and lv[0] == "var":
                out["writes"].append(lv[1:])
            elif lv and lv[0] == "obj":
                out["objw"] = True
            elif lv and lv[0] == "flex":
                out["flex"] = True
            else:
                out["writes"].append(("?",))
        elif eff == "write" and name != "B_PARTYADD":
            out["member_w"] = True
        if name == "B_PARTYADD":
            out["partyadd"] = True
        if o in KEY_OPS:
            m = popped[0] if popped else None
            out["keys"].append((KEY_OPS[o], m[1] if (m and m[0] == "const") else None))
        st.append(("res",))
    return out


_DECODE_FAIL = {"writes": [("?",)], "reads": [], "keys": [], "sysv": set(), "ops": set(), "objw": False,
                "member_w": False, "partyadd": False, "flex": False, "objr": [], "decode_fail": True}


# ------------------------------------------------------------------ per-field model (census, verbatim)
class FieldModel:
    """One field's static facts: entry kinds, the uid map, the DefinePlayerCharacter set, and the field-wide
    MAP/instance var read sites and per-function write sets. ``fid`` is a label only."""

    def __init__(self, eb: EbScript, fid=None):
        self.fid, self.eb, self.data = fid, eb, eb.data
        self.kind = defaultdict(set)          # entry -> {"region","object","code","party-slot","main",...}
        self.uid2e = defaultdict(set)
        self.player = set()
        self._instrs = {}
        self._exprs = {}
        self._effects = {}                    # the latch audit's caches (a promotion add-on, not census state)
        self._flows = {}
        for e in eb.entries:
            if e.empty:
                continue
            for f in e.funcs:
                for ins in self.instrs(e.index, f.tag):
                    if ins.op in (0x07, 0x08, 0x09) and not any(ins.arg_is_expr):
                        sid, uid = ins.args[0], ins.args[1]
                        k = {0x07: "code", 0x08: "region", 0x09: "object"}[ins.op]
                        if 251 <= sid < 255:
                            self.kind[sid].add("party-slot")
                            continue
                        self.kind[sid].add(k)
                        self.uid2e[uid or sid].add(sid)
                    elif ins.op == DEFINE_PLAYER_OP:
                        self.player.add(e.index)
        self.kind[0].add("main")
        for e in eb.entries:     # fallback kinds
            if e.empty or self.kind.get(e.index):
                continue
            f0 = e.funcs[0] if e.funcs else None
            if f0 is None:
                continue
            ops = {i.op for i in self.instrs(e.index, f0.tag)}
            if 0x29 in ops:
                self.kind[e.index].add("region?")
            elif 0x2F in ops:
                self.kind[e.index].add("object?")
        # field-wide var-read index: (entry, tag, off) -> reads
        self.read_sites = []      # (entry, tag, off, src, bits)
        self.write_funcs = defaultdict(list)   # (src) -> [(entry, tag, bits)]
        for e in eb.entries:
            if e.empty:
                continue
            for f in e.funcs:
                for ins in self.instrs(e.index, f.tag):
                    for w in self.expr_info(e.index, f.tag, ins):
                        wr = {(x[0], x[1], x[2]) for x in w["writes"] if len(x) == 3}
                        for (src, typ, idx) in wr:
                            if src in (1, 2):
                                self.write_funcs[src].append((e.index, f.tag, var_bits(typ, idx)))
                        for (src, typ, idx) in w["reads"]:
                            if src in (1, 2) and (src, typ, idx) not in wr:
                                self.read_sites.append((e.index, f.tag, ins.off, src, var_bits(typ, idx)))

    @classmethod
    def from_bytes(cls, data: bytes, fid=None) -> "FieldModel":
        return cls(EbScript.from_bytes(data), fid)

    def func(self, ei, tag):
        if not (0 <= ei < self.eb.entry_count):
            return None
        e = self.eb.entry(ei)
        if e.empty:
            return None
        return e.func_by_tag(tag)

    def instrs(self, ei, tag):
        k = (ei, tag)
        if k not in self._instrs:
            f = self.func(ei, tag)
            try:
                self._instrs[k] = list(self.eb.instrs(f)) if f else []
            except Exception:
                self._instrs[k] = None
        return self._instrs[k] or []

    def decode_failed(self, ei, tag) -> bool:
        self.instrs(ei, tag)
        return self._instrs.get((ei, tag)) is None and self.func(ei, tag) is not None

    def expr_info(self, ei, tag, ins):
        k = (ei, tag, ins.off)
        if k not in self._exprs:
            res = []
            if any(ins.arg_is_expr) or ins.op == 0x05:
                try:
                    for toks in instr_expr_tokens(self.data, ins):
                        if toks:
                            res.append(walk_expr(toks))
                except Exception:
                    res.append(dict(_DECODE_FAIL))
            self._exprs[k] = res
        return self._exprs[k]

    def resolve_uid(self, uid, ctx_entry):
        if uid == SELF_UID:
            return {ctx_entry}, None
        if uid == PLAYER_UID:
            return (set(self.player), None) if self.player else (set(), "player-unresolved")
        if 251 <= uid < 255:
            return set(), "party-slot"
        es = self.uid2e.get(uid)
        if es:
            return set(es), None
        if 0 <= uid < self.eb.entry_count and not self.eb.entry(uid).empty:
            return {uid}, None
        return set(), "uid-unknown"

    def iter_funcs(self):
        """``(entry, tag)`` of every function of every non-empty entry, in table order."""
        for e in self.eb.entries:
            if e.empty:
                continue
            for f in e.funcs:
                yield e.index, f.tag


# ------------------------------------------------------------------ the closure walk
@dataclass(frozen=True)
class Edge:
    """One call the closure walk met. ``kind`` is the DISPATCH kind (module docstring); ``targets`` are the
    entries the call can land on that HAVE the function, ``missing`` the resolved ones that lack it (stock
    no-ops there). ``uid`` / ``tag`` are None when the operand is an expression."""
    src: tuple            # (entry, tag) of the calling function
    off: int              # absolute offset of the call instruction
    op: int
    call: str             # the opcode's name (RunScriptSync, RunSharedScript, InitObject, ...)
    kind: str
    level: int | None
    uid: int | None
    tag: int | None
    targets: tuple
    missing: tuple


class Closure:
    """The transitive closure of one root function (the census's walk, plus edges and fail-closed flags)."""

    def __init__(self, fld: FieldModel, root_entry):
        self.f = fld
        self.root = root_entry
        self.S = Counter()               # effect buckets
        self.seq = []                    # first-occurrence ordered (bucket, ctx)
        self.nodes = []                  # (entry, tag, s, e)
        self.visited = set()
        self.unresolved = Counter()
        self.missing = 0
        self.writes = []                 # (src, typ, idx, exec_entry)
        self.keys = []                   # (kind, mask, ctx)
        self.landing_ops = []            # player-context landing op kinds (coordinates are not kept)
        self.player_calls = []           # (caller_tag, callee_tag, opname)
        self.reads = Counter()
        self.has_loop_player = False
        self.ladder_flag = False
        self.setupjump = 0
        self.jumpop = 0
        self.windows_in_player = 0
        self.node_budget = 300
        self.glob_reads = set()
        self.map_reads = set()
        self.exit_targets = []
        self.decode_fail = False
        self.truncated = False
        self.edges: list[Edge] = []

    def ctx_of(self, ei):
        if ei in self.f.player:
            return "player"
        if ei == self.root:
            return "self"
        return "other"

    def add(self, bucket, ctx):
        if self.S[bucket] == 0:
            self.seq.append((bucket, ctx))
        self.S[bucket] += 1

    def _edge(self, ei, tag, ins, kind, level, uid, ctag, targets, missing):
        self.edges.append(Edge((ei, tag), ins.off, ins.op, ins.name, kind, level, uid, ctag,
                               tuple(sorted(targets)), tuple(sorted(missing))))

    def walk(self, ei, tag, sender=None, actor=None, depth=0):
        key = (ei, tag, None)
        if key in self.visited:
            return
        if depth > 8 or len(self.visited) > self.node_budget:
            self.truncated = True       # the census stops here SILENTLY; an unvisited function could hold anything
            return
        self.visited.add(key)
        ins_list = self.f.instrs(ei, tag)
        if self.f.decode_failed(ei, tag):
            self.decode_fail = True
        if not ins_list:
            if self.f.func(ei, tag) is None:
                self.missing += 1
            return
        s = ins_list[0].off
        e = ins_list[-1].end
        self.nodes.append((ei, tag, s, e))
        actor_e = ei if actor is None else actor          # whose body moves (STARTSEQ keeps the caller's)
        ctx = self.ctx_of(actor_e)
        exit_idx = [k for k, x in enumerate(ins_list) if x.op in (0x2B, 0xB6)]
        for kk, ins in enumerate(ins_list):
            op = ins.op
            bk = B.get(op, "other")
            if op in (0x02, 0x03, 0x01):
                t = jump_target(ins)
                if t is not None and t <= ins.off and ctx == "player":
                    self.has_loop_player = True
            # expressions
            for w in self.f.expr_info(ei, tag, ins):
                if w.get("decode_fail"):
                    self.decode_fail = True
                for wr in w["writes"]:
                    if len(wr) != 3:
                        self.add("other", ctx)
                        continue
                    src, typ, idx = wr
                    self.writes.append((src, typ, idx, actor_e if src == 2 else ei))
                    if src == 0:
                        near_exit = any(0 < j - kk <= 12 for j in exit_idx)
                        if near_exit and not (typ in (6, 7) and idx == 0):
                            self.add("entrance_write" if (typ in (6, 7) and idx == 2) else "exit_glob", ctx)
                        elif typ in (6, 7) and idx == 2:
                            self.add("entrance_write", ctx)
                        elif typ in (6, 7) and idx == 0:
                            self.add("scenario_write", ctx)
                        else:
                            self.add("glob_write", ctx)
                    # map/local decided after the walk (shared vs private)
                for (src, typ, idx) in w["reads"]:
                    if src == 0:
                        self.glob_reads.add((typ, idx))
                        self.reads["glob"] += 1
                    elif src == 1:
                        self.map_reads.add((typ, idx))
                        self.reads["map"] += 1
                for (k, m) in w["keys"]:
                    if m is None:
                        b2 = "key_other"
                    elif m & HOST_OWNED:
                        b2 = "key_press"
                    elif m & DIR_BITS:
                        b2 = "key_dir"
                    else:
                        b2 = "key_other"
                    self.add(b2, ctx)
                    self.keys.append((k, m, ctx))
                if 9 in w["sysv"]:
                    self.add("read_choice", ctx)
                if 0 in w["sysv"] or "B_SELECT" in w["ops"]:
                    self.add("read_rng", ctx)
                if "B_HAVE_ITEM" in w["ops"]:
                    self.add("read_item", ctx)
                if "B_PARTYCHK" in w["ops"]:
                    self.add("read_party", ctx)
                if w["objw"]:
                    self.add("objvar_write", ctx)
                if w["member_w"]:
                    self.add("member_write", ctx)
                if w["partyadd"]:
                    self.add("party_add", ctx)
                if w["flex"]:
                    self.add("flex_expr", ctx)
            if op == 0x05:
                continue
            # opcode effect
            if bk == "locomotion":
                actx = ctx
                if op in EX_TARGET_OPS and ins.args and not ins.arg_is_expr[0]:
                    tgt, why = self.f.resolve_uid(ins.args[0], actor_e)
                    if why == "party-slot":
                        actx = "party"
                    elif tgt:
                        actx = "player" if tgt & self.f.player else ("self" if self.root in tgt else "other")
                if actx == "player":
                    self.add("loco_player", actx)
                    if op in (0xE2, 0xA1, 0x23, 0xA2, 0xAD, 0xBF, 0xE8):
                        self.landing_ops.append(op)
                    if op == 0xCC and ins.imm(0) is not None and ins.imm(0) & 4:
                        self.ladder_flag = True
                    if op == 0xE2:
                        self.setupjump += 1
                    if op == 0xDC:
                        self.jumpop += 1
                elif actx == "self":
                    self.add("loco_self", actx)
                elif actx == "party":
                    self.add("loco_party", actx)
                else:
                    self.add("loco_other", actx)
                continue
            if bk == "window" and ctx == "player":
                self.windows_in_player += 1
            if bk == "exit" and op in (0x2B, 0xB6) and ins.args:
                self.exit_targets.append((op, None if ins.arg_is_expr[0] else ins.args[0]))
            if op == 0x1C and (actor is not None or (ins.args and not ins.arg_is_expr[0] and ins.args[0] == SELF_UID)):
                bk = "flow"                                # a Seq / self ending itself, not a scene change
            if bk not in ("call", "flow"):
                self.add(bk, ctx)
            # calls -- the census's walk, with every edge recorded by its dispatch kind
            if op in CALL_OPS and len(ins.args) >= 3:
                level = ins.imm(0)
                ctag = ins.imm(2)
                if ins.arg_is_expr[1]:
                    self.unresolved["expr-uid"] += 1
                    self._edge(ei, tag, ins, "expr", level, None, ctag, (), ())
                    continue
                uid = ins.args[1]
                tgts, why = self.f.resolve_uid(uid, actor_e)
                tg = ins.args[2]
                if why:
                    self.unresolved[why] += 1
                have = [t for t in sorted(tgts) if self.f.func(t, tg) is not None]
                lack = [t for t in sorted(tgts) if self.f.func(t, tg) is None]
                if ctag is None:
                    kind = "expr"
                elif uid == PLAYER_UID:
                    kind = "ctrl" if not why else "unknown"
                elif uid == SELF_UID:
                    kind = "self"
                elif uid in PARTY_UIDS:
                    kind = "party"
                elif why:
                    kind = "unknown"
                elif tgts and tgts <= self.f.player:
                    kind = "fixed_ctrl"
                else:
                    kind = "fixed_other"
                self._edge(ei, tag, ins, kind, level, uid, ctag, have, lack)
                for t in sorted(tgts):
                    if t in self.f.player:
                        self.player_calls.append((tag, tg, {0x10: "Async", 0x12: "RunScript", 0x14: "Sync"}[op]))
                    if self.f.func(t, tg) is None:
                        self.missing += 1
                        continue
                    self.walk(t, tg, sender=ei, actor=None, depth=depth + 1)
            elif op in SENDER_OPS and len(ins.args) >= 2:
                tg = ins.args[1]
                snd = {sender} if sender is not None else set(self.f.player)
                have = [t for t in sorted(snd) if self.f.func(t, tg) is not None]
                lack = [t for t in sorted(snd) if self.f.func(t, tg) is None]
                self._edge(ei, tag, ins, "sender", ins.imm(0), None, ins.imm(1), have, lack)
                for t in sorted(snd):
                    if self.f.func(t, tg) is None:
                        self.missing += 1
                        continue
                    self.walk(t, tg, sender=ei, actor=None, depth=depth + 1)
            elif op == SEQ_OP and ins.args:
                if ins.arg_is_expr[0]:
                    self.unresolved["expr-seq"] += 1
                    self._edge(ei, tag, ins, "expr", None, None, None, (), ())
                    continue
                t = ins.args[0]
                if 0 <= t < self.f.eb.entry_count and not self.f.eb.entry(t).empty and self.f.eb.entry(t).funcs:
                    ftag = self.f.eb.entry(t).funcs[0].tag
                    self._edge(ei, tag, ins, "seq", None, None, ftag, (t,), ())
                    self.walk(t, ftag, sender=ei, actor=actor_e, depth=depth + 1)
                else:
                    self._edge(ei, tag, ins, "seq", None, None, None, (), (t,))
                    self.missing += 1
            elif op in INIT_OPS and ins.args:
                if ins.arg_is_expr[0]:
                    self.unresolved["expr-init"] += 1
                    self._edge(ei, tag, ins, "expr", None, None, 0, (), ())
                    continue
                t = ins.args[0]
                if 251 <= t < 255:
                    self._edge(ei, tag, ins, "spawn", None, None, 0, (), ())
                    continue
                has = self.f.func(t, 0) is not None
                self._edge(ei, tag, ins, "spawn", None, None, 0, (t,) if has else (), () if has else (t,))
                if has:
                    self.walk(t, 0, sender=ei, actor=None, depth=depth + 1)

    def finish(self):
        """Split MAP/Instance writes into closure-private vs shared (read anywhere outside the closure).
        The census's ORDER-BLIND rule, kept verbatim for the tier; :func:`latch_consumers` is the order-aware
        audit the ship filter reads."""
        def inside(ei, tag, off):
            return any(n[0] == ei and n[1] == tag and n[2] <= off < n[3] for n in self.nodes)
        for (src, typ, idx, owner) in self.writes:
            if src not in (1, 2):
                continue
            bits = var_bits(typ, idx)
            shared = False
            for (ei, tag, off, rsrc, rbits) in self.f.read_sites:
                if rsrc != src or not (rbits & bits):
                    continue
                if src == 2 and ei != owner:
                    continue
                if inside(ei, tag, off):
                    continue
                # a reader that ALSO writes these bits is another SCRATCH user (write-then-read, e.g.
                # every ladder's climb target Map.Int16[2]); only a reader that never writes them is
                # a consumer of the value this closure leaves behind -- a LATCH.
                if any(we == ei and wt == tag and (wb & bits) for (we, wt, wb) in self.f.write_funcs[src]):
                    continue
                shared = True
                break
            if src == 1:
                if (typ, idx) in BRACKET_MAP:
                    self.add("map_bracket", "-")
                else:
                    self.add("map_shared" if shared else "map_private", "-")
            else:
                self.add("local_shared" if shared else "local_private", "-")
        if self.glob_reads:
            self.S["read_glob"] += 1
        if self.map_reads:
            self.S["read_map"] += 1

    def buckets(self):
        return {k for k, v in self.S.items() if v}

    def funcs(self) -> list:
        """The closure's functions ``(entry, tag)`` in DFS discovery order, de-duplicated."""
        out = []
        for (ne, nt, _s, _e) in self.nodes:
            if (ne, nt) not in out:
                out.append((ne, nt))
        return out


# ------------------------------------------------------------------ classification (census, verbatim)
def classify(c: Closure):
    S = c.buckets()
    loco_p = "loco_player" in S
    loco_any = loco_p or ("loco_self" in S) or ("loco_other" in S) or ("loco_party" in S)
    win = "window" in S
    choice = "choice" in S or "read_choice" in S
    persist = S & PERSIST
    hard = S & HARD
    latch = S & LATCH
    scene = S & SCENE
    exits = "exit" in S
    reasons = sorted(persist | hard | latch | scene | ({"exit"} if exits else set()) |
                     ({"window"} if win else set()) | ({"choice"} if choice else set()))
    if "exit_glob" in S and not exits:
        persist = persist | {"glob_write"}
    meaningful = S - NEUTRAL - {"entrance_write", "loco_self", "exit_glob"}
    if not meaningful and not loco_any:
        return "TRIVIAL", reasons
    if persist or hard:
        return "STATEFUL", reasons
    if exits:
        if win or choice:
            return "STATEFUL", reasons            # a talk that ends in a warp ("go to X?")
        return ("LOCO+EXIT" if loco_p else "EXIT-ONLY"), reasons
    if win:
        if scene:
            return "STATEFUL", reasons
        if latch:
            return "FLAVOR+LATCH", reasons
        return ("FLAVOR+CHOICE" if choice else "FLAVOR-TALK"), reasons
    if choice:
        return "STATEFUL", reasons
    if loco_p:
        if scene - {"loco_other"}:
            return "STATEFUL", reasons
        if "loco_other" in S:
            return ("LOCO+ACTORS+LATCH" if latch else "LOCO+ACTORS"), reasons
        if latch:
            return "LOCO+LATCH", reasons
        return "LOCO-ONLY", reasons
    # no player motion, no window
    if scene or latch:
        return "SCENE-LOCAL", reasons             # props/tiles/NPC motion only, no persistence
    return "COSMETIC-ONLY", reasons


def loco_kind(c: Closure):
    if not ("loco_player" in c.buckets()):
        return None
    dir_keys = any(k[1] is not None and (k[1] & DIR_BITS) and not (k[1] & HOST_OWNED) for k in c.keys)
    if c.ladder_flag and dir_keys:
        return "ladder-navigable"
    if c.ladder_flag:
        return "ladder-auto"
    if c.setupjump and c.jumpop:
        return "jump"
    if c.has_loop_player and not dir_keys:
        return "carry-loop"
    if any(op in (0x23, 0xA2, 0xE8) for op in c.landing_ops):
        return "walk"
    if any(op in (0xA1, 0xAD, 0xBF) for op in c.landing_ops):
        return "teleport"
    return "anim-only"


def root_gate(fld: FieldModel, ei, tag):
    """What the ROOT function's own guards read before acting: usercontrol / glob / map / item / party."""
    g = set()
    for ins in fld.instrs(ei, tag):
        if ins.op != 0x05:
            continue
        for w in fld.expr_info(ei, tag, ins):
            if w["writes"]:
                continue
            for (src, typ, idx) in w["reads"]:
                if src == 1 and typ in (0, 1) and idx in BRACKET_READ_BITS:
                    continue                                  # the stock control-macro selectors
                if src == 0 and typ in (6, 7) and idx == 0:
                    g.add("scenario")
                    continue
                g.add({0: "glob", 1: "map", 2: "local", 3: "null"}[src])
            if 2 in w["sysv"]:
                g.add("usercontrol")
            if "B_HAVE_ITEM" in w["ops"]:
                g.add("item")
            if "B_PARTYCHK" in w["ops"]:
                g.add("party")
    return g


# ------------------------------------------------------------------ QUAD roots and verdicts
def quad_roots(fld: FieldModel) -> list:
    """Region entries with a tag-3 function: the census's QUAD roots (an entry that is both a region and an
    object counts as a region, as the census has it)."""
    out = []
    for e in fld.eb.entries:
        if e.empty or e.index == 0:
            continue
        kinds = fld.kind.get(e.index, set())
        isreg = bool(kinds & {"region", "region?"})
        if isreg and any(f.tag == 3 for f in e.funcs):
            out.append(e.index)
    return out


@dataclass(frozen=True)
class PressVerdict:
    """What pressing one region runs. ``tier`` and ``kind`` are the census's names (LOCO-ONLY, LOCO+LATCH, ...;
    ladder-navigable, jump, ...); ``funcs`` the closure's ``(entry, tag)`` in DFS order; ``closure`` the walked
    :class:`Closure` (its edges, writes and flags)."""
    region: int
    tier: str
    kind: str | None
    gate: tuple
    funcs: tuple
    edges: tuple
    player_entries: tuple
    missing: int
    truncated: bool
    decode_fail: bool
    unresolved: tuple
    buckets: tuple
    reasons: tuple
    closure: Closure

    @property
    def candidate(self) -> bool:
        """The census's guest-traversal candidate: a LOCO-ONLY press closure that moves the player."""
        return self.tier == "LOCO-ONLY" and self.kind in MOVERS


def analyze_root(fld: FieldModel, ei: int, tag: int = 3) -> PressVerdict:
    """The closure of one root function (``tag`` 3 for a press; the far-tread report also walks tag 2)."""
    c = Closure(fld, ei)
    c.walk(ei, tag)
    c.finish()
    cls, reasons = classify(c)
    return PressVerdict(ei, cls, loco_kind(c), tuple(sorted(root_gate(fld, ei, tag))), tuple(c.funcs()),
                        tuple(c.edges), tuple(sorted(fld.player)), c.missing, c.truncated, c.decode_fail,
                        tuple(sorted(c.unresolved.items())), tuple(sorted(c.buckets())), tuple(reasons), c)


def analyze_regions(eb_or_model) -> list:
    """One :class:`PressVerdict` per QUAD root of a field (an :class:`EbScript`, raw bytes, or a
    :class:`FieldModel`), in entry order."""
    fld = _model(eb_or_model)
    return [analyze_root(fld, ei, 3) for ei in quad_roots(fld)]


def _model(x) -> FieldModel:
    if isinstance(x, FieldModel):
        return x
    if isinstance(x, (bytes, bytearray)):
        return FieldModel.from_bytes(bytes(x))
    return FieldModel(x)


# ------------------------------------------------------------------ the path-aware latch audit
@dataclass(frozen=True)
class LatchReader:
    """An outside function's access to a MAP (src 1) / instance (src 2) var the closure writes. ``first`` is
    ``"read"`` when some path from the function's start READS a bit of it before a plain write covers that bit
    (:func:`latch_access`), else ``"write"``; ``off`` is the first uncovered read (or, write-first, the first
    access); ``exempt_why`` is None, or the load-once trace when a read-first reader can only ever run during
    field init."""
    entry: int
    tag: int
    var: tuple            # (src, typ, idx) -- the closure's written var
    first: str
    off: int              # absolute offset of the first uncovered read / the first access
    rel: int              # ... relative to the function's start
    exempt_why: str | None

    @property
    def consumer(self) -> bool:
        """A read-first reader that is NOT load-once: it can consume a value the press left behind."""
        return self.first == "read" and self.exempt_why is None

    @property
    def label(self) -> str:
        return f"{self.entry}:{self.tag}"


def _token_effects(toks) -> list:
    """One decoded token list's var tokens, in token order: ``(src, typ, idx, covers)``. ``covers`` is True only for
    the lvalue of a plain ``B_LET``; every other var token is a READ -- the lvalue of a compound ``*_LET`` or of a
    ``++`` / ``--`` (read-modify-write), an RHS self-read (``x = x + 1``), an operand or an index. The stack walk
    mirrors :func:`walk_expr` token for token."""
    occ, st = [], []
    for (o, v) in toks:
        if o == 0x7F:
            break
        if o == 0xD3:
            _fid, argc = v
            for _ in range(min(argc, len(st))):
                st.pop()
            st.append(None)
            continue
        if o in (0x7D, 0x7E):
            st.append(None)
            continue
        if o >= 0xC0:
            occ.append([o & 3, (o >> 2) & 7, v, False])
            st.append(len(occ) - 1)
            continue
        if o in (0x78, 0x7A, 0x79, 0x29, 0x5F):
            st.append(None)
            continue
        name = EXPR_OP_NAMES.get(o, f"op{o:02X}")
        ar = OP_SEMANTICS.get(name, (0, "read"))[0]
        popped = [st.pop() if st else None for _ in range(ar)]
        popped.reverse()
        if name == PURE_LET and popped and popped[0] is not None:
            occ[popped[0]][3] = True
        st.append(None)
    return [tuple(x) for x in occ]


def var_effects(fld: FieldModel, ei: int, tag: int, ins) -> "tuple | None":
    """The latch audit's view of one instruction: every var token of every expression operand, as
    :func:`_token_effects` gives it, or None when an expression fails to decode (read as a read of everything)."""
    k = (ei, tag, ins.off)
    if k not in fld._effects:
        out = []
        if any(ins.arg_is_expr) or ins.op == 0x05:
            try:
                for toks in instr_expr_tokens(fld.data, ins):
                    if toks:
                        out += _token_effects(toks)
            except Exception:
                out = None
        fld._effects[k] = None if out is None else tuple(out)
    return fld._effects[k]


def _access(fld: FieldModel, ei: int, tag: int, ins, src: int, bits) -> "tuple[frozenset, frozenset]":
    """``(read bits, covered bits)`` of one instruction on ``bits`` of var source ``src``. A write covers only its
    OWN bits (a ``Byte[2]`` store leaves the top byte of an ``Int16[2]`` uncovered)."""
    eff = var_effects(fld, ei, tag, ins)
    if eff is None:
        return frozenset(bits), frozenset()
    r, w = set(), set()
    for (s, t, i, covers) in eff:
        if s == src:
            (w if covers else r).update(var_bits(t, i) & bits)
    return frozenset(r), frozenset(w)


def is_const_self_end(ins) -> bool:
    """TerminateEntry as the CONSTANT self-end: flag bit 0 clear and operand 255. Any other form disposes another
    object (EBin.cs case 28 -> DisposeObj) and its caller runs on."""
    return ins.op == TERMINATE_OP and bool(ins.args) and not ins.arg_is_expr[0] and ins.args[0] == SELF_UID


def _ends_path(ins) -> bool:
    """A path ENDS at a flow terminator (disasm.TERMINATOR_OPS: RET, Battle, Field, STOP, ...); TerminateEntry ends
    it only as the constant self-end 255."""
    if ins.op == TERMINATE_OP:
        return is_const_self_end(ins)
    return ins.op in TERMINATOR_OPS


def _flow(fld: FieldModel, ei: int, tag: int) -> "FuncFlow | None":
    k = (ei, tag)
    if k not in fld._flows:
        f = fld.func(ei, tag)
        try:
            fld._flows[k] = FuncFlow.build(fld.data, f.abs_start, f.abs_end) if f is not None else None
        except Exception:                         # CfgError or a malformed stream: the caller fails closed
            fld._flows[k] = None
    return fld._flows[k]


def latch_access(fld: FieldModel, ei: int, tag: int, src: int, bits) -> "tuple[list, int] | None":
    """How ``(ei, tag)`` touches ``bits`` of var source ``src``: None when it never does, else ``(uncovered, first)``
    -- the sorted absolute offsets of its UNCOVERED reads and the offset of its first access in byte order.

    A forward MAY-UNCOVERED dataflow over the function's CFG (``eb.cfg.FuncFlow``: JMP / JMP_IF / JMP_IFNOT edges,
    every switch arm plus its default, RET and the flow terminators end a path, TerminateEntry only as the constant
    255): the function's start is seeded with ALL of ``bits`` uncovered, a plain ``B_LET`` covers its own bits on its
    own path, a join unions the uncovered bits of its predecessors, and a read that touches any bit still uncovered
    where it runs is an uncovered read (inside one instruction the reads come first, so ``x = x + 1`` reads). Fails
    CLOSED: a function that does not decode, or whose CFG does not build, reads at its start."""
    f = fld.func(ei, tag)
    if f is None:
        return None
    if fld.decode_failed(ei, tag):
        return [f.abs_start], f.abs_start
    acc = {ins.off: _access(fld, ei, tag, ins, src, bits) for ins in fld.instrs(ei, tag)}
    touch = [off for off, (r, w) in acc.items() if r or w]
    if not touch:
        return None
    first = min(touch)
    if not any(r for (r, _w) in acc.values()):
        return [], first
    flow = _flow(fld, ei, tag)
    if flow is None or not flow.blocks:
        return [f.abs_start], first

    def at(ins):
        a = acc.get(ins.off)
        return a if a is not None else _access(fld, ei, tag, ins, src, bits)

    blocks = flow.blocks
    unc = {flow.entry: frozenset(bits)}          # block -> the bits a path may reach its start with still uncovered
    work = [flow.entry]
    while work:
        b = work.pop()
        cur = set(unc[b])
        for ins in blocks[b].instrs:
            cur -= at(ins)[1]
            if _ends_path(ins):
                break
        else:
            out = frozenset(cur)
            for (s, _c) in blocks[b].succs:
                if s not in unc or not out <= unc[s]:
                    unc[s] = unc.get(s, frozenset()) | out
                    work.append(s)
    reads = []
    for b in sorted(unc):
        cur = set(unc[b])
        for ins in blocks[b].instrs:
            r, w = at(ins)
            if r & cur:
                reads.append(ins.off)
            cur -= w
            if _ends_path(ins):
                break
    return sorted(reads), first


def _first_back_target(fld: FieldModel, ei: int, tag: int) -> "int | None":
    """The smallest backward-jump target (absolute) in ``(ei, tag)``, or None when nothing jumps backward."""
    back = [t for ins in fld.instrs(ei, tag) if ins.op in BACK_JUMP_OPS
            for t in [jump_target(ins)] if t is not None and t <= ins.off]
    return min(back) if back else None


def load_once_why(fld: FieldModel, ei: int, tag: int, read_off: int) -> "str | None":
    """Why the reader ``(ei, tag)`` whose LATEST uncovered read is at ``read_off`` can only run during field init, or
    None when it is not provably load-once. ALL of (critique G5's tighter rule):

    * it is a tag-0 or tag-1 function of an entry other than 0 (tag 0 runs when the object is created; tag 1 runs
      once when tag 0 returns, EventEngine.cs:1279-1283);
    * nothing targets it: no ``RunScript*`` whose uid can resolve to the entry (250, 255 from the entry itself,
      a party slot, an unknown or computed uid all count) with that tag or a computed one, and no
      ``RunScriptObject*`` with that tag or a computed one;
    * nothing RESTARTS it (a tag-1 reader only): no ``ReturnEntryFunctions`` anywhere whose operand is an expression,
      does not resolve, or resolves to the entry (250 for a player entry, 255 from the entry itself) -- DRET aborts
      the target's functions and restarts its tag 1 (EventEngine.DoEventCode.cs DRET -> Return: sx 0, stateInit ->
      ``ip = GetIP(sid, 1)``); tag 0 never re-runs, so a tag-0 reader keeps its exemption;
    * EVERY uncovered read comes before its first backward-jump target (none of them is inside a loop), in a
      function that decodes and whose CFG builds (a computed jump leaves the loop question open);
    * its entry is created ONLY by entry 0's tag-0 Init* (field init): no other InitObject / InitRegion / InitCode
      of it, no Init* with a computed or party-slot entry outside entry 0's tag 0, and no ``RunSharedScript`` of it
      (a Seq re-runs an entry's tag 0) or a computed one anywhere.
    """
    if ei == 0 or tag not in (0, 1) or fld.decode_failed(ei, tag) or _flow(fld, ei, tag) is None:
        return None
    born_at_init = False
    for (ce, ct) in fld.iter_funcs():
        for ins in fld.instrs(ce, ct):
            op = ins.op
            if op in CALL_OPS and len(ins.args) >= 3:
                if ins.arg_is_expr[2] or ins.args[2] == tag:
                    if ins.arg_is_expr[1]:
                        return None
                    tgts, why = fld.resolve_uid(ins.args[1], ce)
                    if why or ei in tgts:
                        return None
            elif op in SENDER_OPS and len(ins.args) >= 2:
                if ins.arg_is_expr[1] or ins.args[1] == tag:
                    return None
            elif op == SEQ_OP and ins.args:
                if ins.arg_is_expr[0] or ins.args[0] == ei:
                    return None
            elif op == RETURN_ENTRY_OP and tag == 1:
                if not ins.args or ins.arg_is_expr[0]:
                    return None
                tgts, why = fld.resolve_uid(ins.args[0], ce)
                if why or ei in tgts:
                    return None
            elif op in INIT_OPS and ins.args:
                at_init = (ce, ct) == (0, 0)
                if ins.arg_is_expr[0] or 251 <= ins.args[0] < 255:
                    if not at_init:
                        return None
                    continue
                if ins.args[0] == ei:
                    if not at_init:
                        return None
                    born_at_init = True
    if not born_at_init:
        return None
    back = _first_back_target(fld, ei, tag)
    if back is not None and read_off >= back:
        return None
    f = fld.func(ei, tag)
    rel = read_off - f.abs_start
    loop = "no backward jump" if back is None else f"its first backward-jump target is +{back - f.abs_start}"
    return (f"{ei}:{tag} is load-once: created only by 0:0's Init*, no RunScript*/RunScriptObject*/Seq targets "
            f"it{', no ReturnEntryFunctions restarts it' if tag == 1 else ''}, and its last uncovered read (+{rel}) "
            f"is before any loop ({loop})")


def latch_consumers(eb_or_model, verdict: PressVerdict) -> list:
    """The path-aware latch audit of one press closure: for every MAP / instance var the closure writes (the talk
    bracket's Map.Bit[158] excepted, as the census has it), EVERY function outside the closure that touches it --
    not only the census's read sites, which miss a read-modify-write-only reader -- with its :func:`latch_access`
    verdict. Instance vars (src 2) count only inside their owner entry (the census's rule). A read-first reader that
    is not load-once (:func:`load_once_why`, checked at its LATEST uncovered read) is a latch CONSUMER
    (:attr:`LatchReader.consumer`) -- the ship filter's R11."""
    fld = _model(eb_or_model)
    c = verdict.closure
    inside = set(verdict.funcs)
    owners = defaultdict(set)                     # (src, typ, idx) -> the entries whose instance copy is written
    for (src, typ, idx, owner) in c.writes:
        if src not in (1, 2) or (src == 1 and (typ, idx) in BRACKET_MAP):
            continue
        owners[(src, typ, idx)].add(owner)
    funcs = list(dict.fromkeys(fld.iter_funcs()))
    out = []
    for var in sorted(owners):
        src, typ, idx = var
        bits = var_bits(typ, idx)
        for (re_, rt) in funcs:
            if (re_, rt) in inside or (src == 2 and re_ not in owners[var]):
                continue
            acc = latch_access(fld, re_, rt, src, bits)
            if acc is None:
                continue
            reads, first = acc
            start = fld.func(re_, rt).abs_start
            if reads:
                why = load_once_why(fld, re_, rt, reads[-1])
                out.append(LatchReader(re_, rt, var, "read", reads[0], reads[0] - start, why))
            else:
                out.append(LatchReader(re_, rt, var, "write", first, first - start, None))
    out.sort(key=lambda r: (r.var, r.entry, r.tag))
    return out
