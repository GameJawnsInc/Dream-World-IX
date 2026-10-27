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
* **Where.** Every key poll and every player landing op is also recorded with its function and offset
  (``Closure.key_sites``, ``Closure.landings`` -- the landing's constant x / y / z, :func:`place_point`), for the
  ship filter's R14 (key) and R15 (walk-in); the buckets they feed are untouched.
* **The WATCHER scan** (:func:`watch_scan`). What a function the engine starts on its own -- and everything it
  calls -- can do with no press at all: its key polls, its reads of the controlled player's whereabouts, and its
  effect ops, each with the FACTS every path to it establishes (:func:`func_facts`: a dominating branch that
  proves user control is on, or that a constant Confirm / Special / Select poll fired). ONE fact does not survive a
  yield or a control write (:func:`facts_after`, :data:`YIELD_OPS`): the two halves count only proved in one frame,
  and only the proved pair carries into a callee (:func:`carried`). The ship filter's R16 and R15's walk-in
  exemption read it (:meth:`WatchScan.exempt_why`, FAIL CLOSED: a closed scan that visited every closure function,
  and a site for every STATEFUL bucket of the closure, :func:`site_buckets`); the census never sees it.
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
from dataclasses import dataclass, field

from ._exprtable import EXPR_OP_NAMES, decode_var
from ._optables import OP_ARG_COUNT
from .cfg import FuncFlow
from .disasm import TERMINATOR_OPS, decode_switch, instr_expr_tokens, jump_target
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


#: the placement and landing ops -> the operand index of x, y, z (None = the op carries no y); an Ex op's operand 0
#: is the moved object's uid
PLACE_ARGS = {0x1D: (0, None, 1),             # CreateObject(x, z)
              0x23: (0, None, 1),             # Walk(x, z)
              0xA1: (0, 1, 2),                # MoveInstantXZY(x, y, z)
              0xA2: (0, 1, 2),                # WalkXZY(x, y, z)
              0xAD: (1, 2, 3),                # MoveInstantXZYEx(uid, x, y, z)
              0xBF: (1, None, 2),             # MoveInstantEx(uid, x, z)
              0xE2: (0, 1, 2),                # SetupJump(x, y, z, steps)
              0xE8: (0, 1, 2)}                # SideWalkXZY(x, y, z)


def place_point(ins) -> tuple:
    """``(op, x, y, z)`` of a placement / landing op (:data:`PLACE_ARGS`): each coordinate its signed constant, None
    when that operand is an expression or the op carries none."""
    def at(i):
        if i is None or i >= len(ins.args) or ins.arg_is_expr[i]:
            return None
        return s16(ins.args[i])
    xi, yi, zi = PLACE_ARGS[ins.op]
    return ins.op, at(xi), at(yi), at(zi)


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
                got = list(self.eb.instrs(f)) if f else []
                self._instrs[k] = None if any(i.op == STACKED_PREFIX_OP for i in got) else got
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
        self.key_sites = []              # ... and where: (kind, mask, bucket, (entry, tag), off) -- R14 reads it
        self.landing_ops = []            # player-context landing op kinds
        self.landings = []               # ... and their points: (op, x, y, z, (entry, tag), off), None = computed
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
                    self.key_sites.append((k, m, b2, (ei, tag), ins.off))
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
                        self.landings.append(place_point(ins) + ((ei, tag), ins.off))
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


# ------------------------------------------------------------------ the watcher scan (R16, and R15's walk-in exemption)
#: what a FOLLOWING guest's control-ON field poll loses: NetSyncField.ControlOnScriptKeys(keys, false) =
#: keys & ~(Confirm | Special | Select) -- F1's free-walk mask (NetSyncField.cs:955-958, called at :892). Every other
#: host-owned bit (Circle, Cross, Cancel, ...) still reaches a control-on poll.
F1_STRIPPED = CONFIRM | SPECIAL | SELECT
#: EventInput.Cancel (EventInput.cs:553): where ETb.ProcessJapaneseLayout (ETb.cs:80-89) moves a physical Confirm in a
#: Japanese game BEFORE the filter sees it (EBin.cs:1106 / :1137 read ETb.KeyOn / GetInputs(CurrentSymbol == "JP"))
CANCEL = 0x10000
#: guest_traversal's JP WAIVER hypothesis: F1's mask once ControlOnScriptKeys also strips the Cancel bit a Japanese
#: guest's Confirm lands on (the engine follow-up) -- a Japanese chest's KEYON(Cancel | Special) then proves a press too
JP_F1_STRIPPED = F1_STRIPPED | CANCEL
#: the key reads EBin routes through NetSyncField.FilterScriptButtons: B_KEYON (EBin.cs:1096-1110) and B_KEY
#: (:1131-1140). B_KEYOFF (:1125-1129) is never filtered; B_KEYON2 / B_KEYOFF2 / B_KEY2 read 0
#: (EventEngine.DoCalcOperationExt.cs:7, :67-70)
FILTERED_KEY_OPS = frozenset({0x4F, 0x59})
#: the ops after which a script's next instruction may run in a LATER frame, other objects having run between: the
#: interpreter leaves an object whenever an op returns non-zero (EBin.next / adfr, EBin.cs:188-221) -- EBin.wait (Wait,
#: :1341-1372) and every EventEngine.DoEventCode case that can return non-zero or stay() (EventEngine.DoEventCode.cs, by
#: case line): NOTHING :50, RunScript :154, RunScriptSync :186, RunScriptObject :236, RunScriptObjectSync :250,
#: WindowSync :410, WindowAsync :461, WindowSyncEx / WindowAsyncEx :506, CloseWindow :527, WaitWindow :569, ChangeDisc
#: :604, Walk :656, WalkTowardObject :798, WalkEx :806, WalkXZY :847, WalkToExit :872, Slide :878, SideWalkXZY :892,
#: Battle :957, BattleEx :985, Field :1016, WaitAnimation :1420, WaitAnimationEx :1427, WaitSharedScript :1472, 0x4F
#: :1665, WaitTurn / WaitTurnEx :1672, SetModelColor :2088, Jump :2137, ReturnEntryFunctions :2172, DisableMenu :2356,
#: Menu :2364, Party :2390, GameOver :2427, TetraMaster :2433, WorldMap :2513 -- and every opcode with no case at all
#: (default: return 1, :3387-3390). Bubble (FICON, :1889-1902) returns 0: it does not yield. RunScriptAsync (REQ,
#: :144-152) returns 0 but yields when its uid names the executing object (255 outside a Seq, its own uid, a computed
#: one): Request -> Call (EventEngine.cs:340-372) points the CURRENT object's ip at the callee, which runs inline, and
#: the callee's RET ends the object's run (EBin.jumpToCommand case 4: Return + adfr) -- the caller resumes in a later one;
#: it counts as a yield whatever its uid (FAIL CLOSED). Every code PAST the enum yields too (:func:`is_yield`)
YIELD_OPS = frozenset({0x00, 0x10, 0x12, 0x14, 0x18, 0x1A, 0x1F, 0x20, 0x21, 0x22, 0x23, 0x24, 0x2A, 0x2B, 0x41, 0x44,
                       0x4F, 0x50, 0x54, 0x75, 0x8C, 0x8F, 0x95, 0x96, 0x97, 0xA0, 0xA2, 0xA5, 0xAB, 0xAC, 0xAE, 0xB2,
                       0xB6, 0xBC, 0xBE, 0xDC, 0xE8, 0xF5, 0x117,
                       0x0A, 0x0C, 0x0E, 0x0F, 0x11, 0x13, 0x15, 0x17, 0x19, 0x6E, 0x11F})
#: the first code past the engine's opcode enum (EBin.event_code_binary ends at REMOVE_STATUS 0x11E): OP_ARG_COUNT's
#: length, 0x11F. disasm.read_code decodes ``0xFF XX`` as ``0x100 | XX`` for ANY XX, so a decoded op can be anything up to
#: 0x1FF -- and none of those codes has a DoEventCode case (default: return 1, EventEngine.DoEventCode.cs:3387-3390)
OP_PAST_ENUM = len(OP_ARG_COUNT)
#: what disasm.read_code makes of STACKED prefixes ``0xFF 0xFF XX``: the engine loops over them (DoEventCode.cs:35-42,
#: code += 0x100 per prefix) and runs ONE op 0x200 + XX -- the default case, after which commandDefault2 backs ip up one
#: byte (EBin.cs:1421-1434) -- where the disassembler reads 0x1FF and then decodes XX as an op of its own, out of step
#: with the engine; FieldModel.instrs counts such a function as one that does not decode (FAIL CLOSED). Stock has none.
STACKED_PREFIX_OP = 0x1FF


def is_yield(op: int) -> bool:
    """``op`` may end the object's run for this frame: :data:`YIELD_OPS`, or any code at or past :data:`OP_PAST_ENUM`
    (the default case's ``return 1``) -- FAIL CLOSED for a code the kit's tables never name."""
    return op in YIELD_OPS or op >= OP_PAST_ENUM


#: user control's writers inside one frame (EventEngine.DoEventCode.cs): DisableMove :1059-1061 and ExitField :859-866
#: set _context.usercontrol = 0, EnableMove :1077-1079 sets it 1
CONTROL_OFF_OPS, CONTROL_ON_OPS = frozenset({0x2D, 0x9E}), frozenset({0x2E})
#: every census bucket classify can turn into STATEFUL -- alone (PERSIST, HARD, a choice), with a window or the player's
#: own motion (SCENE), an exit with a window, exit_glob with no exit -- the sites the walk-in exemption must see
STATEFUL_BUCKETS = frozenset(PERSIST | HARD | SCENE | {"exit", "window", "choice", "read_choice", "exit_glob"})
#: B_SYSVAR[2] = EventEngine.GetSysvar(2) = _context.usercontrol (GetSysvar.cs:17-18): root_gate's "usercontrol"
USERCONTROL_SYSVAR = 2
#: B_SYSVAR[4] = EventCollision.sSysAngle, the controlled player's angle to the object it collided with
#: (EventCollision.cs:115, :281) -- a read of where the player stands
PLAYER_ANGLE_SYSVAR = 4
CONTROL, KEY = "control", "key"             # the facts a dominating branch can establish (:func:`cond_facts`)
BOTH = frozenset({CONTROL, KEY})
#: an instruction's effect, by the census's opcode bucket (guest_traversal's effect classes, widened to every HARD /
#: PERSIST bucket an opcode carries)
EFFECT_BUCKETS = {"exit": "exit", "battle": "battle", "window": "window", "choice": "window", "item_party": "item",
                  "menu": "menu", "fmv": "fmv", "ate": "ate", "world": "world", "flex_state": "flex state"}
#: expression operators that read an object's whereabouts through an operand uid (EBin.cs:1188-1201 B_DISTANCEA,
#: :1172-1187 B_ANGLEA; DoCalcOperationExt.cs:42-49 B_BGIID / B_BGIFLOOR) -- the first two also read the executing
#: object's own position, as B_ANGLE / B_DISTANCE do (EBin.cs:1141-1164)
UID_POS_OPS = {0x60: "B_ANGLEA", 0x61: "B_DISTANCEA", 0x70: "B_BGIID", 0x71: "B_BGIFLOOR"}
SELF_POS_OPS = {0x5D: "B_ANGLE", 0x5E: "B_DISTANCE", 0x60: "B_ANGLEA", 0x61: "B_DISTANCEA"}
SCREEN_POS_OP = 0xA9                        # CalculateScreenPosition(uid): sSysX / sSysY from the object's position
_WATCH_DEPTH, _WATCH_BUDGET = 8, 300        # watch_scan's bounds (the closure walk's own)
_CMP3 = {24: lambda a, b: a < b, 25: lambda a, b: a > b, 26: lambda a, b: a <= b, 27: lambda a, b: a >= b,
         32: lambda a, b: a == b, 33: lambda a, b: a != b}


def eval3(toks, hyp) -> "int | None":
    """One expression's value under a HYPOTHESIS, three-valued. ``hyp(o, v, arg)`` names the value of a B_SYSVAR
    (``o`` 0x7A, ``v`` its code) or of a key read (``o`` a KEY_OPS token, ``arg`` its mask when that is constant):
    an int, or None when it does not know; every other leaf is unknown. The result is an int only when it holds for
    EVERY value of the unknowns -- ``0 && x`` and ``0 & x`` are 0, ``1 || x`` is 1, a comparison or ``!`` needs
    known operands -- else None. The stack walk is :func:`walk_expr`'s (each operator's true arity)."""
    st = []
    for (o, v) in toks or ():
        if o == 0x7F:
            break
        if o == 0xD3:
            for _ in range(min(v[1], len(st))):
                st.pop()
            st.append(None)
            continue
        if o in (0x7D, 0x7E):
            st.append(s16(v) if o == 0x7D else v)
            continue
        if o == 0x7A:
            st.append(hyp(o, v, None))
            continue
        if o >= 0xC0 or o in (0x78, 0x79, 0x29, 0x5F):
            st.append(None)
            continue
        ar = OP_SEMANTICS.get(EXPR_OP_NAMES.get(o, f"op{o:02X}"), (0, "read"))[0]
        args = [st.pop() if st else None for _ in range(ar)][::-1]
        if o in KEY_OPS:
            st.append(hyp(o, None, args[0] if args else None))
        elif o in _CMP3 and len(args) == 2 and None not in args:
            st.append(int(_CMP3[o](*args)))
        elif o == 14 and len(args) == 1 and args[0] is not None:          # B_NOT (logical)
            st.append(int(not args[0]))
        elif o in (36, 39) and len(args) == 2:                            # B_AND / B_ANDAND: a known 0 decides it
            a, b = args
            st.append(0 if 0 in (a, b) else None if None in (a, b) else (a & b if o == 36 else int(bool(a and b))))
        elif o == 40 and len(args) == 2:                                  # B_OROR: a known non-zero decides it
            a, b = args
            st.append(1 if any(x not in (None, 0) for x in (a, b)) else 0 if (a, b) == (0, 0) else None)
        else:
            st.append(None)
    return st[-1] if st else None


def _control_off(o, v, arg):
    return 0 if (o == 0x7A and v == USERCONTROL_SYSVAR) else None


def _stripped_polls_miss(stripped):
    """The F1 hypothesis under mask ``stripped``: every filtered poll of a constant, non-zero mask inside it reads 0."""
    return lambda o, v, arg: 0 if (o in FILTERED_KEY_OPS and arg and not (arg & ~stripped)) else None


def cond_facts(toks, stripped=F1_STRIPPED) -> "tuple[frozenset, frozenset]":
    """``(when true, when false)``: the facts a branch on this condition establishes on each outcome. CONTROL when the
    condition is decided with user control OFF (B_SYSVAR[2] = 0: if that makes it false, a true outcome proves control
    on); KEY when it is decided with every filtered poll of a constant mask inside ``stripped`` (F1_STRIPPED) missing (a
    true outcome then proves such a poll fired -- which F1 forbids a following guest at control-on)."""
    uc, ky = eval3(toks, _control_off), eval3(toks, _stripped_polls_miss(stripped))
    when_true = frozenset(f for f, r in ((CONTROL, uc), (KEY, ky)) if r == 0)
    when_false = frozenset(f for f, r in ((CONTROL, uc), (KEY, ky)) if r not in (None, 0))
    return when_true, when_false


def facts_after(facts: frozenset, ins) -> frozenset:
    """The CONTROL / KEY facts still proved once ``ins`` has run. BOTH together survive anything: a following guest's
    control was on at the test and off at the poll (F1 strips it at control-on) within one frame and no control write
    -- a contradiction, so no guest's path gets past that point at all. ONE alone does not survive a yield (YIELD_OPS:
    other objects run and control can change before the other half is proved -- FilterScriptButtons decides the mask
    at the KEYON read, NetSyncField.cs:858; :func:`is_yield`), CONTROL not an op that turns control off, KEY (control off
    at its poll) not one that turns it on."""
    if BOTH <= facts:
        return facts
    if is_yield(ins.op):
        return facts - BOTH
    if ins.op in CONTROL_OFF_OPS:
        return facts - {CONTROL}
    if ins.op in CONTROL_ON_OPS:
        return facts - {KEY}
    return facts


def carried(facts: frozenset) -> frozenset:
    """The CONTROL / KEY facts a callee is entered with -- a RunScript* target, a Seq, an Init*-created object. Its code
    runs in a later segment (EventEngine.Request -> Call only sets the target's ip, EventEngine.cs:340-372: it runs when
    the interpreter reaches that object), so only BOTH carry: the call site itself is then out of every guest's reach."""
    return facts & BOTH if BOTH <= facts else frozenset()


def branch_facts(fld: FieldModel, flow: FuncFlow, b: int, end: int, stripped=F1_STRIPPED) -> dict:
    """``{successor block: facts}`` for block ``b``'s JMP_IF / JMP_IFNOT on the SET right before it (eb.cfg's branch
    idiom); a successor both outcomes reach keeps only what both prove. No facts for a switch, an unconditional edge,
    a jump with no SET before it, or a condition that does not decode."""
    blk = flow.blocks[b]
    last = blk.instrs[-1]
    if last.op not in (0x02, 0x03) or len(blk.instrs) < 2 or blk.instrs[-2].op != 0x05:
        return {}
    try:
        toks = instr_expr_tokens(fld.data, blk.instrs[-2])[0]
    except Exception:                             # noqa: BLE001 -- an undecodable condition proves nothing
        return {}
    when_true, when_false = cond_facts(toks, stripped)
    taken, fall = (when_true, when_false) if last.op == 0x03 else (when_false, when_true)
    t = jump_target(last)
    out = {}
    for at, facts in ((None if last.end >= end else flow.block_at(last.end), fall),
                      (None if t is None or t >= end else flow.block_at(t), taken)):
        if at is not None:
            out[at] = facts if at not in out else out[at] & facts
    return out


def func_facts(fld: FieldModel, ei: int, tag: int, ctx=frozenset(), stripped=F1_STRIPPED) -> "dict | None":
    """block -> the facts EVERY path from the function's start (entered holding ``ctx``) to that block's start
    establishes -- a forward MUST dataflow (a join keeps what all its paths prove; each instruction passes them through
    :func:`facts_after`; a path ends at a flow terminator, TerminateEntry only as the constant self-end). Unreachable
    blocks are absent. None when the function does not decode or its CFG does not build (the caller fails closed)."""
    f = fld.func(ei, tag)
    flow = _flow(fld, ei, tag)
    if f is None or flow is None or not flow.blocks or fld.decode_failed(ei, tag):
        return None
    facts = {flow.entry: frozenset(ctx)}
    work = [flow.entry]
    while work:
        b = work.pop()
        if any(_ends_path(ins) for ins in flow.blocks[b].instrs):
            continue
        bf = branch_facts(fld, flow, b, f.abs_end, stripped)
        out = facts[b]
        for ins in flow.blocks[b].instrs:
            out = facts_after(out, ins)
        for (s, _c) in flow.blocks[b].succs:
            new = out | bf.get(s, frozenset())
            if s not in facts:
                facts[s] = new
                work.append(s)
            elif not facts[s] <= new:
                facts[s] = facts[s] & new
                work.append(s)
    return facts


def names_player(fld: FieldModel, uid, actor) -> bool:
    """``uid`` (read in ``actor``'s code) can name the controlled player: 250, the uid of a DefinePlayerCharacter
    entry, 255 inside a player entry, a party slot, None (computed) or a uid that does not resolve (FAIL CLOSED)."""
    if uid is None or uid == PLAYER_UID or 251 <= uid < 255:
        return True
    if uid == SELF_UID:
        return actor in fld.player
    tgts, why = fld.resolve_uid(uid, actor)
    return bool(why) or bool(tgts & fld.player)


def player_reads(fld: FieldModel, toks, actor) -> list:
    """The reads of the controlled player's whereabouts in one expression run by ``actor``, as text: ``obj(uid).f[0..2]``
    (B_OBJSPECA: x, y, z -- EBin.cs getvobj cases 0-2), B_MEMBER's f[0..2] (a computed object), B_DISTANCEA /
    B_ANGLEA / B_BGIID / B_BGIFLOOR of a uid that can name the player (:func:`names_player`; a computed one counts),
    B_ANGLE / B_DISTANCE / B_ANGLEA / B_DISTANCEA run by a player entry (they read the executing object's own position)
    and B_SYSVAR[4] (the player's collision angle)."""
    out, st = [], []
    for (o, v) in toks or ():
        if o == 0x7F:
            break
        if o == 0xD3:
            for _ in range(min(v[1], len(st))):
                st.pop()
            st.append(None)
            continue
        if o in (0x7D, 0x7E, 0x5F):                   # a constant, or B_PTR(uid): the uid itself
            st.append(v)
            continue
        if o == 0x78:
            if v[1] in (0, 1, 2) and names_player(fld, v[0], actor):
                out.append(f"obj(uid={v[0]}).f[{v[1]}]")
            st.append(None)
            continue
        if o == 0x29:
            if v in (0, 1, 2):
                out.append(f"B_MEMBER f[{v}] (a computed object)")
            st.append(None)
            continue
        if o == 0x7A:
            if v == PLAYER_ANGLE_SYSVAR:
                out.append("B_SYSVAR[4] (the player's collision angle)")
            st.append(None)
            continue
        if o >= 0xC0 or o == 0x79:
            st.append(None)
            continue
        ar = OP_SEMANTICS.get(EXPR_OP_NAMES.get(o, f"op{o:02X}"), (0, "read"))[0]
        args = [st.pop() if st else None for _ in range(ar)][::-1]
        if o in UID_POS_OPS and args and names_player(fld, args[0], actor):
            out.append(f"{UID_POS_OPS[o]}({'a computed uid' if args[0] is None else args[0]})")
        elif o in SELF_POS_OPS and actor in fld.player:
            out.append(f"{SELF_POS_OPS[o]} by a player entry")
        st.append(None)
    return out


def site_buckets(fld: FieldModel, node, ins, actor, seq: bool, root: int, near_exit: bool) -> set:
    """The census buckets ONE instruction adds to its closure -- Closure.walk's own rules, instruction by instruction
    (its expression writes and reads, the opcode's bucket, a locomotion op's target context, the Seq / self-end
    TerminateEntry), so the walk-in exemption can name the site behind each bucket of a closure. ``actor`` is whose body
    runs it (a Seq keeps its caller's), ``root`` the scanned root's entry, ``near_exit`` an exit op within the census's
    12 instructions after it."""
    ei, tag = node
    out = set()
    for w in fld.expr_info(ei, tag, ins):
        for wr in w["writes"]:
            if len(wr) != 3:
                out.add("other")
            elif wr[0] == 0:
                typ, idx = wr[1], wr[2]
                if near_exit and not (typ in (6, 7) and idx == 0):
                    out.add("entrance_write" if (typ in (6, 7) and idx == 2) else "exit_glob")
                elif typ in (6, 7) and idx in (0, 2):
                    out.add("scenario_write" if idx == 0 else "entrance_write")
                else:
                    out.add("glob_write")
        if 9 in w["sysv"]:
            out.add("read_choice")
        out |= {bk for flag, bk in (("objw", "objvar_write"), ("member_w", "member_write"), ("partyadd", "party_add"),
                                    ("flex", "flex_expr")) if w[flag]}
    if ins.op == 0x05:
        return out
    bk = B.get(ins.op, "other")
    if bk == "locomotion":
        ctx = "player" if actor in fld.player else ("self" if actor == root else "other")
        if ins.op in EX_TARGET_OPS and ins.args and not ins.arg_is_expr[0]:
            tgt, why = fld.resolve_uid(ins.args[0], actor)
            if why == "party-slot":
                ctx = "party"
            elif tgt:
                ctx = "player" if tgt & fld.player else ("self" if root in tgt else "other")
        return out | {"loco_" + ctx}
    if ins.op == TERMINATE_OP and (seq or is_const_self_end(ins)):
        return out                                # a Seq / self ending itself: "flow"
    return out | ({bk} - {"call", "flow"})


def one_tag_zero(fld: FieldModel, t) -> bool:
    """Entry ``t`` holds exactly ONE function, tag 0 -- the only Seq entry whose run the closure walk (which takes the
    entry's FIRST listed function, census-verbatim) sees whole. RunSharedScript (STARTSEQ, EventEngine.DoEventCode.cs
    :1444-1471) builds ``new Seq(entry, uid)``: the Obj constructor points it at ``GetIP(sid, 0)`` -- found by TAG id, in
    any listed order (EventEngine.GetIP, EventEngine.cs:1116-1137) -- in stateNew, EBin.ProcessCode moves it to stateInit
    (EBin.cs:115-119), and when that tag 0 returns EventEngine.Return (stateInit, EventEngine.cs:1278-1283) points it at
    ``GetIP(sid, 1)``: the entry's TAG 1 runs next, as the Seq, on the caller's body."""
    return 0 <= t < fld.eb.entry_count and not fld.eb.entry(t).empty and [f.tag for f in fld.eb.entry(t).funcs] == [0]


def closure_gaps(v: "PressVerdict") -> list:
    """Why the closure walk of ``v`` did not see everything (FAIL CLOSED -- R15 holds such a walk-in EXPOSED whatever
    its tier): a truncated walk, a decode failure, an unresolved uid / tag / entry, a call with an expression, unknown
    or party target -- and the tag 1 a walked op starts, which the walk never follows: an Init*-created entry that has
    one runs it when its tag 0 returns (EventEngine.Return, stateInit -> ``ip = GetIP(sid, 1)``, EventEngine.cs:1278-1283),
    ReturnEntryFunctions restarts its target's (EventEngine.DoEventCode.cs DRET :2172-2181: ``sx = 0``, stateInit,
    Return), and a Seq whose entry is not :func:`one_tag_zero` runs its tag 1 when its tag 0 returns (and the walk took
    the entry's first listed function, which need not be its tag 0)."""
    out = []
    if v.truncated:
        out.append("the walk was truncated")
    if v.decode_fail:
        out.append("an instruction or expression failed to decode")
    if v.unresolved:
        out.append("unresolved " + ", ".join(f"{k} x{n}" for k, n in v.unresolved))
    out += [f"{ed.src[0]}:{ed.src[1]} {ed.call} has a {ed.kind} target" for ed in v.edges
            if ed.kind in ("expr", "unknown", "party")]
    fld = v.closure.f
    out += [f"{ed.src[0]}:{ed.src[1]} {ed.call} creates {t}, whose tag 1 runs when its tag 0 returns"
            for ed in v.edges if ed.kind == "spawn" for t in ed.targets + ed.missing if fld.func(t, 1) is not None]
    out += [f"{ei}:{tag} ReturnEntryFunctions restarts an entry's tag 1" for (ei, tag) in v.funcs
            if any(ins.op == RETURN_ENTRY_OP for ins in fld.instrs(ei, tag))]
    out += [f"{ed.src[0]}:{ed.src[1]} RunSharedScript({t}) runs a Seq whose entry is not one tag 0 (its tag 1 runs when "
            "its tag 0 returns)" for ed in v.edges if ed.kind == "seq" for t in ed.targets + ed.missing
            if not one_tag_zero(fld, t)]
    return out


def effects_of(fld: FieldModel, ei: int, tag: int, ins) -> list:
    """One instruction's effect classes: its opcode's (:data:`EFFECT_BUCKETS`) and its expressions' -- a Global or
    Null var write, a write whose target is not a var, a party add or member write, a flexible-varfunc call."""
    out = []
    eff = EFFECT_BUCKETS.get(B.get(ins.op))
    if eff:
        out.append(eff)
    for w in fld.expr_info(ei, tag, ins):
        for wr in w["writes"]:
            if len(wr) != 3:
                out.append("a computed write")
            elif wr[0] in (0, 3):
                out.append("GLOB write" if wr[0] == 0 else "Null write")
        if w["partyadd"]:
            out.append("item")
        if w["member_w"]:
            out.append("member write")
        if w["flex"]:
            out.append("flex")
    return out


def control_deps(fld: FieldModel, ei: int, tag: int) -> "dict | None":
    """block -> the BRANCH blocks it is control-dependent on, transitively (a branch decides whether the block runs:
    the block post-dominates one of the branch's successors but not the branch). Post-dominators over the reachable
    blocks plus a virtual exit that every path end (RET, the function's end, a flow terminator) and every LOOP LATCH
    (a block with an edge back to an equal-or-earlier block) reaches -- one iteration of a tag-1 loop is a path, so an
    endless loop still has post-dominators. None when the CFG does not build (FAIL CLOSED)."""
    f = fld.func(ei, tag)
    flow = _flow(fld, ei, tag)
    if f is None or flow is None or not flow.blocks or fld.decode_failed(ei, tag):
        return None
    blocks = flow.blocks
    ends = {b for b, blk in enumerate(blocks) if any(_ends_path(i) for i in blk.instrs)}
    reach, work = set(), [flow.entry]
    while work:
        b = work.pop()
        if b in reach:
            continue
        reach.add(b)
        if b not in ends:
            work += [s for (s, _c) in blocks[b].succs]
    EXIT = -1
    succ = {}
    for b in reach:
        last = blocks[b].instrs[-1]
        succ[b] = set() if b in ends else {s for (s, _c) in blocks[b].succs}
        if b in ends or not succ[b] or any(blocks[s].start <= blocks[b].start for s in succ[b]):
            succ[b].add(EXIT)                     # a path end, or a latch: one iteration ends here
        if b not in ends and last.op in (0x02, 0x03) and (last.end >= f.abs_end or (jump_target(last) or f.abs_end)
                                                          >= f.abs_end):
            succ[b].add(EXIT)                     # a conditional jump or its fall-through leaves the function
        if b not in ends and last.op in (0x06, 0x0B, 0x0D):
            si = decode_switch(last)
            if si is None or any(e.target >= f.abs_end for e in si.edges) or last.end >= f.abs_end:
                succ[b].add(EXIT)                 # a switch arm (or the default) leaves the function
    every = frozenset(reach) | {EXIT}
    pdom = {b: every for b in reach}
    pdom[EXIT] = frozenset({EXIT})
    changed = True
    while changed:
        changed = False
        for b in reach:
            m = frozenset.intersection(*(pdom[s] for s in succ[b])) | {b}
            if m != pdom[b]:
                pdom[b], changed = m, True

    def ipdom(b):
        strict = pdom[b] - {b}
        return next((d for d in strict if pdom[d] == strict), EXIT)
    cd = defaultdict(set)
    for a in reach:
        if a in ends or blocks[a].instrs[-1].op not in (0x02, 0x03, 0x06, 0x0B, 0x0D):
            continue                              # not a branch (a latch's exit edge is virtual)
        stop = ipdom(a)
        for s in succ[a]:
            t = s
            while t != EXIT and t != stop:
                cd[t].add(a)
                t = ipdom(t)
    out = {}
    for b in reach:                               # the transitive closure: a branch's own dependences carry
        seen, stack = set(), list(cd.get(b, ()))
        while stack:
            a = stack.pop()
            if a not in seen:
                seen.add(a)
                stack += cd.get(a, ())
        out[b] = frozenset(seen)
    return out


def branch_cond(fld: FieldModel, flow: FuncFlow, b: int) -> "list | None":
    """The condition tokens of block ``b``'s branch -- the SET right before its JMP_IF / JMP_IFNOT / switch (eb.cfg's
    idiom) -- or None when the branch has no SET there or it does not decode (the value it tests is unknown)."""
    blk = flow.blocks[b]
    if len(blk.instrs) < 2 or blk.instrs[-2].op != 0x05:
        return None
    try:
        return instr_expr_tokens(fld.data, blk.instrs[-2])[0]
    except Exception:                             # noqa: BLE001
        return None


POS, HOSTKEY = "position", "host key"     # what an effect's firing can depend on (watch_scan's TRIGGER flags)


@dataclass
class Taint:
    """The vars whose value can carry the controlled player's whereabouts (``pos``) or a host-owned key poll's
    outcome (``key``), per var source as a set of bits (var_bits: a Byte inside an Int16 overlaps it): a var written by
    an expression that reads one (data), or written where the write's firing depends on one (control). ``screen``:
    the field computes a CalculateScreenPosition that can name the player, so B_SYSVAR[12] / [13] (sSysX / sSysY,
    EventEngine.DoEventCode.cs:2343) carry its position."""
    pos: dict
    key: dict
    screen: bool = False

    @classmethod
    def empty(cls, screen=False) -> "Taint":
        return cls(defaultdict(frozenset), defaultdict(frozenset), screen)

    def reads(self, which: str, toks) -> bool:
        tbl = self.pos if which == POS else self.key
        for (o, v) in toks or ():
            if o == 0x7F:
                break
            if o >= 0xC0 and o != 0xD3 and var_bits((o >> 2) & 7, v) & tbl.get(o & 3, frozenset()):
                return True
            if which == POS and o == 0x7A and self.screen and v in (12, 13):
                return True
        return False

    def same(self, other: "Taint") -> bool:
        def norm(t):
            return {k: v for k, v in t.items() if v}
        return norm(self.pos) == norm(other.pos) and norm(self.key) == norm(other.key)


def _host_poll(toks) -> bool:
    """The expression polls a host-owned key (HOST_OWNED) or a computed mask -- any key read."""
    w = walk_expr(toks)
    return any(m is None or m & HOST_OWNED for (_k, m) in w["keys"])


def cond_triggers(fld: FieldModel, toks, actor, taint: Taint) -> frozenset:
    """What a branch on this condition makes its dependents' firing depend on: POS when it reads the controlled
    player's whereabouts (:func:`player_reads`) or a POS-tainted var, HOSTKEY when it polls a host-owned or computed
    key or reads a KEY-tainted var. None (no SET before the branch, an undecodable one) is BOTH (FAIL CLOSED)."""
    if toks is None:
        return frozenset({POS, HOSTKEY})
    out = set()
    if player_reads(fld, toks, actor) or taint.reads(POS, toks):
        out.add(POS)
    if _host_poll(toks) or taint.reads(HOSTKEY, toks):
        out.add(HOSTKEY)
    return frozenset(out)


@dataclass(frozen=True)
class WatchSite:
    """One site watch_scan met: ``node`` (entry, tag), its absolute ``off``, ``what`` it is, and its ``facts``: CONTROL
    / KEY when every path from the scanned root to it passes a branch proving them (:func:`func_facts`), POS /
    HOSTKEY when its firing depends on a branch reading them (:func:`control_deps`, :func:`cond_triggers`)."""
    node: tuple
    off: int
    what: str
    facts: frozenset

    def at(self, fld: FieldModel) -> str:
        return f"{self.node[0]}:{self.node[1]} +{self.off - fld.func(*self.node).abs_start}"


@dataclass
class WatchScan:
    """What one root function and everything it calls can do with no press: ``polls`` (``(site, mask)``, mask None =
    computed), ``reads`` (of the controlled player's whereabouts), ``effects``, ``writes`` (``(var, triggers)``: every
    var write with what its value or its firing depends on -- the field's taint) and ``open`` -- why the scan could
    not see everything (a CFG that does not build, a computed or unresolvable call, a sender call, the walk's bounds).
    ``nodes``: the functions it visited; ``stateful``: every site of a :data:`STATEFUL_BUCKETS` census bucket (its
    ``what`` the bucket, :func:`site_buckets`). FAIL CLOSED: an open scan is never exempt and always trips R16."""
    root: tuple
    polls: list
    reads: list
    effects: list
    writes: list
    open: list
    nodes: set = field(default_factory=set)
    stateful: list = field(default_factory=list)

    def host_polls(self) -> list:
        """The polls of a host-owned or computed mask -- any key read (B_KEYOFF is not even filtered)."""
        return [p for (p, mask) in self.polls if mask is None or mask & HOST_OWNED]

    def uncovered(self, fact: str) -> list:
        return [e for e in self.effects if fact not in e.facts]

    def key_triggered(self) -> list:
        """(a): the effects whose firing depends on a host-owned key poll and that no user-control test dominates --
        a following guest's OWN press reaches them while a guest-local climb holds control off (FilterScriptButtons
        masks a control-off poll only under ScriptKeyLockActive, NetSyncField.cs:894-907)."""
        return [e for e in self.effects if HOSTKEY in e.facts and CONTROL not in e.facts]

    def position_triggered(self) -> list:
        """(b): the effects whose firing depends on the controlled player's whereabouts and that no constant poll F1
        strips at control-on dominates -- the climb carries the guest where its own copy fires them."""
        return [e for e in self.effects if POS in e.facts and KEY not in e.facts]

    def exempt_why(self, v: PressVerdict) -> "str | None":
        """None when the HIDDEN-ITEM exemption holds for the scanned root's closure ``v`` (its PressVerdict), else why
        not -- FAIL CLOSED, in order: (a) the scan is open; (b) the closure reaches a function the scan never visited;
        (c) a bucket of the closure that can make it STATEFUL (:data:`STATEFUL_BUCKETS`) has no site in the scan; then
        any effect or STATEFUL-bucket site not dominated by BOTH a user-control test and a constant poll inside the
        scan's mask -- with both, it can fire neither with control off (the test) nor at control-on (F1's mask)."""
        if self.open:
            return f"its scan is open ({self.open[0]})"
        unseen = [n for n in v.funcs if n not in self.nodes]
        if unseen:
            return f"the scan never visited {unseen[0][0]}:{unseen[0][1]}"
        lost = sorted(set(v.buckets) & STATEFUL_BUCKETS - {s.what for s in self.stateful})
        if lost:
            return f"its closure's {lost[0]} has no site the scan saw"
        for s in self.effects + self.stateful:
            if not BOTH <= s.facts:
                return f"{s.what} at {s.node[0]}:{s.node[1]} is not under both a user-control test and a stripped poll"
        return None


def watch_scan(fld: FieldModel, ei: int, tag: int, taint: "Taint | None" = None, *, spawn: bool = False,
               stripped: int = F1_STRIPPED) -> WatchScan:
    """Scan root ``(ei, tag)`` and every function it calls -- RunScript* into its targets' code, RunSharedScript into
    the Seq target's tag 0 (by tag id, :func:`one_tag_zero`) and its tag 1 (it runs when that returns) on the caller's
    object -- each callee entered holding the triggers at its call site and the
    facts that carry (:func:`carried`). Init* is followed only with ``spawn`` (R15's walk-ins: the closure walk follows
    it), into the created entry's tag 0; for R16 the object it creates runs its own tag 0 / tag 1, which
    :func:`watch_roots` lists. ``taint`` is the field's (:func:`field_watch` computes it; without one nothing is
    tainted); ``stripped`` the control-on mask a KEY fact needs (F1_STRIPPED; JP_F1_STRIPPED is the JP waiver's)."""
    taint = taint or Taint.empty()
    ws = WatchScan((ei, tag), [], [], [], [], [])
    seen = set()

    def visit(node, actor, seq, ctx, trig, depth):
        if (node, actor, seq, ctx, trig) in seen:
            return
        if depth > _WATCH_DEPTH or len(seen) > _WATCH_BUDGET:
            ws.open.append(f"{node[0]}:{node[1]} is past the walk's depth / node budget")
            return
        seen.add((node, actor, seq, ctx, trig))
        if fld.func(*node) is None:
            return                                    # a missing function: the stock no-op
        ws.nodes.add(node)
        facts = func_facts(fld, node[0], node[1], ctx, stripped)
        deps = control_deps(fld, node[0], node[1])
        if facts is None or deps is None:
            ws.open.append(f"{node[0]}:{node[1]}'s CFG does not build")
            return
        flow = _flow(fld, *node)
        listed = fld.instrs(*node)
        pos = {x.off: k for k, x in enumerate(listed)}
        exits = [k for k, x in enumerate(listed) if x.op in (0x2B, 0xB6)]
        branch = {}
        for b in sorted(facts):
            got = set(trig)
            for a in deps.get(b, ()):
                if a not in branch:
                    branch[a] = cond_triggers(fld, branch_cond(fld, flow, a), actor, taint)
                got |= branch[a]
            cur = facts[b]
            for ins in flow.blocks[b].instrs:
                near = any(0 < j - pos.get(ins.off, -99) <= 12 for j in exits)
                site(node, actor, seq, cur | got, frozenset(got), depth, ins, near)
                cur = facts_after(cur, ins)
                if _ends_path(ins):
                    break

    def site(node, actor, seq, have, trig, depth, ins, near):
        where = f"{node[0]}:{node[1]} +{ins.off - fld.func(*node).abs_start}"
        if any(ins.arg_is_expr) or ins.op == 0x05:
            try:
                toks = instr_expr_tokens(fld.data, ins)
            except Exception:                         # noqa: BLE001 -- an undecodable operand hides anything
                ws.open.append(f"{where} does not decode")
                toks = []
            for t in toks:
                if not t:
                    continue
                for r in player_reads(fld, t, actor):
                    ws.reads.append(WatchSite(node, ins.off, r, have))
                w = walk_expr(t)
                for (k, m) in w["keys"]:
                    what = f"{k}({'a computed mask' if m is None else '0x%X' % m})"
                    ws.polls.append((WatchSite(node, ins.off, what, have), m))
                data = set(trig)
                if player_reads(fld, t, actor) or taint.reads(POS, t):
                    data.add(POS)
                if _host_poll(t) or taint.reads(HOSTKEY, t):
                    data.add(HOSTKEY)
                for wr in w["writes"]:
                    if len(wr) == 3:
                        ws.writes.append((tuple(wr), frozenset(data), have & {CONTROL, KEY}))
        for e in effects_of(fld, node[0], node[1], ins):
            ws.effects.append(WatchSite(node, ins.off, e, have))
        for bk in sorted(site_buckets(fld, node, ins, actor, seq, ei, near) & STATEFUL_BUCKETS):
            ws.stateful.append(WatchSite(node, ins.off, bk, have))
        op = ins.op
        if op == SCREEN_POS_OP and ins.args:
            uid = None if ins.arg_is_expr[0] else ins.args[0]
            if names_player(fld, uid, actor):
                what = f"CalculateScreenPosition({'a computed uid' if uid is None else uid})"
                ws.reads.append(WatchSite(node, ins.off, what, have))
        if op in CALL_OPS and len(ins.args) >= 3:
            if ins.arg_is_expr[1] or ins.arg_is_expr[2]:
                ws.open.append(f"{where} {ins.name} has a computed uid or tag")
                return
            tgts, why = fld.resolve_uid(ins.args[1], actor)
            if why:
                ws.open.append(f"{where} {ins.name}(uid {ins.args[1]}) does not resolve ({why})")
                return
            for t in sorted(tgts):
                if fld.func(t, ins.args[2]) is not None:
                    visit((t, ins.args[2]), t, False, carried(have), trig, depth + 1)
        elif op in SENDER_OPS:
            ws.open.append(f"{where} {ins.name} runs its sender's code (unknown to a root)")
        elif op == SEQ_OP and ins.args:
            if ins.arg_is_expr[0]:
                ws.open.append(f"{where} RunSharedScript has a computed entry")
                return
            t = ins.args[0]
            for stag in (0, 1):                       # GetIP(sid, 0) BY TAG, then its tag 1 when that returns
                if fld.func(t, stag) is not None:
                    visit((t, stag), actor, True, carried(have), trig, depth + 1)
        elif spawn and op in INIT_OPS and ins.args:
            if ins.arg_is_expr[0] or 251 <= ins.args[0] < 255:
                ws.open.append(f"{where} {ins.name} creates a computed or party-slot entry")
                return
            if fld.func(ins.args[0], 0) is not None:
                visit((ins.args[0], 0), ins.args[0], False, carried(have), trig, depth + 1)

    visit((ei, tag), ei, False, frozenset(), frozenset(), 0)
    return ws


def watch_roots(fld: FieldModel) -> list:
    """The functions the engine starts on its own on a guest's copy: every entry's tag 0 (Obj: ip = GetIP(sid, 0),
    Obj.cs:51) and tag 1 (when tag 0 returns, EventEngine.cs:1282), and entry 0's tag 10 (Main_Reinit after a battle,
    EventEngine.cs:689). The other engine-started tags are judged elsewhere: tag 2 (a tread or a bump,
    EventCollision.cs:305-312) by R15; tags 3 and 8 (a press, a card) a following guest never starts but for the
    CRC-checked rows (CheckQuadInput EventCollision.cs:73-86, CheckNPCInput :115-119)."""
    return list(dict.fromkeys((e.index, f.tag) for e in fld.eb.entries if not e.empty
                              for f in e.funcs if f.tag in (0, 1) or (e.index == 0 and f.tag == 10)))


_TAINT_ROUNDS = 8
#: the var sources a trigger taints: Map and Instance. A Global or Null write is itself an EFFECT (effects_of), so a chain
#: through one already trips at its writer -- the guest-triggerable write is the finding, not what later reads it
TAINT_SOURCES = (1, 2)


def field_watch(fld: FieldModel) -> dict:
    """``{root: WatchScan}`` for every :func:`watch_roots` root under the field's :class:`Taint`, a FIXPOINT: every
    function of the field is scanned as its own root (a callee also inside its callers' contexts), and a Map / Instance
    var write a guest can trigger taints its var with what its value or firing depends on -- POS when that is the
    player's whereabouts and no F1-stripped poll dominates the write, HOSTKEY when it is a host-owned key poll and no
    user-control test dominates it -- until no var is newly tainted. A taint that does not settle in its rounds marks
    every scan open (FAIL CLOSED)."""
    screen = any(ins.op == SCREEN_POS_OP and ins.args and
                 names_player(fld, None if ins.arg_is_expr[0] else ins.args[0], ei)
                 for (ei, tag) in fld.iter_funcs() for ins in fld.instrs(ei, tag))
    taint = Taint.empty(screen)
    funcs = list(dict.fromkeys(fld.iter_funcs()))
    for _ in range(_TAINT_ROUNDS):
        scans = {node: watch_scan(fld, *node, taint) for node in funcs}
        new = Taint.empty(screen)
        for ws in scans.values():
            for ((src, typ, idx), trig, facts) in ws.writes:
                if src not in TAINT_SOURCES:
                    continue
                if POS in trig and KEY not in facts:
                    new.pos[src] = new.pos[src] | var_bits(typ, idx)
                if HOSTKEY in trig and CONTROL not in facts:
                    new.key[src] = new.key[src] | var_bits(typ, idx)
        for which in ("pos", "key"):
            mine, theirs = getattr(new, which), getattr(taint, which)
            for k, v in theirs.items():
                mine[k] = mine[k] | v
        if new.same(taint):
            return {r: scans[r] for r in watch_roots(fld) if r in scans}
        taint = new
    out = {r: scans[r] for r in watch_roots(fld) if r in scans}
    for ws in out.values():
        ws.open.append(f"the field's position / key taint did not settle in {_TAINT_ROUNDS} rounds")
    return out
