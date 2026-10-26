#!/usr/bin/env python3
"""PRESS-FIRED INTERACTION census over every real FF9 field -- which interactions could a co-op GUEST run
LOCALLY (ladders, climbs, jumps, lifts...) instead of being blocked by NetSyncField.SpectatorField?

READ-ONLY. Reads every field's English (US) ``.eb`` LIVE from the Steam install via UnityPy and decodes RAW
opcodes / expression tokens through the worktree kit's byte-exact ``eb`` model (never text transcripts).

ROOTS (what the engine fires on a button press -- engine-grounded, see the report for file:line):
  * QUAD  : a region entry's tag-3 function  -- EventCollision.CheckQuadInput -> TreadQuad(po,4) -> Request(obj,1,3)
  * NPC   : an object entry's tag-3 function -- EventCollision.CheckNPCInput -> Request(obj,1,3)
  * TREAD-POLL : the Confirm/Special-guarded span inside a tag-2 (tread/push) function -- the stock CHEST idiom
            (Request(obj,1,2) every tread frame; the press is an in-script B_KEYON). Blocked for a guest by
            NetSyncField.FilterScriptButtons' control-on mask, not by Check*Input.
  * LOOP-POLL : a Confirm/Special-guarded forward span inside a tag-1 (loop) function (secondary; may include
            control-off scene waits -- reported separately, not merged into the headline).
  * CARD  : tag-8 (Special -> Tetra Master challenge) -- counted only.

TRANSITIVE CLOSURE: RunScriptAsync/RunScript/RunScriptSync (0x10/0x12/0x14: level, uid, tag) resolve uid ->
entry (250 = controlUID -> every DefinePlayerCharacter entry; 255 = self; 251-254 = party, unresolved; else the
InitObject/InitRegion/InitCode uid map, default uid == entry index); RunScriptObject* (0x16/0x18/0x1A: level, tag)
target the SENDER (the caller; the engine-started root's sender is the player); RunSharedScript (0x43, entry)
runs that entry's first function on the CURRENT object; Init* (0x07-0x09) spawn and are followed into tag 0.
Inline DFS in instruction order (so "what happens first" is preserved), depth/node budgets, visited guard.

Usage:  py interaction_census.py [--json OUT.json] [--limit N] [--walkmesh]
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

WT = Path(__file__).resolve().parents[3]   # the repo root this study lives in (studies/field-coop/guest-traversal/)
sys.path.insert(0, str(WT / "ff9mapkit"))
import ff9mapkit  # noqa: E402
assert Path(ff9mapkit.__file__).resolve().is_relative_to(WT.resolve()), ff9mapkit.__file__

from ff9mapkit.eb import EbScript                      # noqa: E402
from ff9mapkit.eb.disasm import jump_target, instr_expr_tokens  # noqa: E402
from ff9mapkit.eb._exprtable import EXPR_OP_NAMES      # noqa: E402
from ff9mapkit.eb.exprsem import OP_SEMANTICS          # noqa: E402
from ff9mapkit.extract import EventBundle              # noqa: E402
from ff9mapkit._fieldtable import FIELD_BY_ID          # noqa: E402

# ------------------------------------------------------------------ engine constants
CONFIRM, SPECIAL, SELECT = 0x20000, 0x80000, 0x1
CIRCLE, CROSS = 0x2000, 0x4000
DIR_BITS = 0x10 | 0x20 | 0x40 | 0x80
HOST_OWNED = (SELECT | 0x1000 | CIRCLE | CROSS | 0x8000 | 0x10000 | CONFIRM | 0x40000 | SPECIAL | 0x1000000)
PRESS_BITS = CONFIRM | SPECIAL            # the free-walk interaction bits (CheckQuadInput's mask)
PLAYER_UID, SELF_UID = 250, 255
KEY_OPS = {0x4F: "KEYON", 0x58: "KEYOFF", 0x59: "KEY", 0x5A: "KEYON2", 0x5B: "KEYOFF2", 0x5C: "KEY2"}
LET2 = {"B_LET", "B_MULT_LET", "B_DIV_LET", "B_REM_LET", "B_PLUS_LET", "B_MINUS_LET", "B_SHIFT_LEFT_LET",
        "B_SHIFT_RIGHT_LET", "B_AND_LET", "B_XOR_LET", "B_OR_LET"}
INCDEC = {"B_POST_PLUS", "B_POST_MINUS", "B_PRE_PLUS", "B_PRE_MINUS"}
VT_BITS = {0: 1, 1: 1, 2: 24, 3: 24, 4: 8, 5: 8, 6: 16, 7: 16}

# ------------------------------------------------------------------ opcode -> effect bucket
B = {}
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


MAPW = Counter()
EXITGLOBW = Counter()
GLOBW = Counter()
# the stock control-macro MAP bits (the talk bracket: 158 = "bracket closed" bookkeeping, set 0 at entry and 1
# at exit by EVERY stock talk; 159/144/156 are its READ-only selectors). Data-driven below (--mapw).
BRACKET_MAP = {(1, 158)}
BRACKET_READ_BITS = {144, 156, 158, 159}   # read by the bracket's own conditions (ignored as a "gate")


def s16(v):
    return v - 65536 if v >= 32768 else v


def var_bits(typ, idx):
    if typ in (0, 1):
        return frozenset([idx])
    n = VT_BITS.get(typ, 8)
    return frozenset(range(idx * 8, idx * 8 + n))


# ------------------------------------------------------------------ expression walker
def walk_expr(toks):
    """RPN-walk one decoded token list. Returns dict: writes=[(src,typ,idx,kind)], reads=[(src,typ,idx)],
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
            st.append(("const", v)); continue
        if o >= 0xC0:
            src, typ = o & 3, (o >> 2) & 7
            out["reads"].append((src, typ, v))
            st.append(("var", src, typ, v)); continue
        if o == 0x78:
            out["objr"].append(v)
            st.append(("obj", v)); continue
        if o == 0x7A:
            out["sysv"].add(v); st.append(("sys", v)); continue
        if o in (0x79, 0x29, 0x5F):
            st.append(("misc", o, v)); continue
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


# ------------------------------------------------------------------ per-field model
class Field:
    def __init__(self, fid, eb: EbScript):
        self.fid, self.eb, self.data = fid, eb, eb.data
        self.kind = defaultdict(set)          # entry -> {"region","object","code","party"}
        self.uid2e = defaultdict(set)
        self.player = set()
        self._instrs = {}
        self._exprs = {}
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
                    elif ins.op == 0x2C:
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
                    res.append({"writes": [("?",)], "reads": [], "keys": [], "sysv": set(), "ops": set(),
                                "objw": False, "member_w": False, "partyadd": False, "flex": False,
                                "objr": [], "decode_fail": True})
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


# ------------------------------------------------------------------ closure walk
class Closure:
    def __init__(self, fld: Field, root_entry):
        self.f = fld
        self.root = root_entry
        self.S = Counter()               # effect buckets
        self.seq = []                    # first-occurrence ordered (bucket, ctx)
        self.nodes = []                  # (entry, tag, s, e)
        self.visited = set()
        self.unresolved = Counter()
        self.missing = 0
        self.writes = []                 # (src, typ, idx, exec_entry)
        self.keys = []                   # (kind, mask, ctx, in_loop)
        self.landings = []               # (op, x, y, z) player ctx immediates
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

    def walk(self, ei, tag, span=None, sender=None, actor=None, depth=0):
        key = (ei, tag, span)
        if key in self.visited or depth > 8 or len(self.visited) > self.node_budget:
            return
        self.visited.add(key)
        ins_list = self.f.instrs(ei, tag)
        if self.f._instrs.get((ei, tag)) is None and self.f.func(ei, tag) is not None:
            self.decode_fail = True
        if not ins_list:
            if self.f.func(ei, tag) is None:
                self.missing += 1
            return
        s = span[0] if span else ins_list[0].off
        e = span[1] if span else (ins_list[-1].end)
        self.nodes.append((ei, tag, s, e))
        actor_e = ei if actor is None else actor          # whose body moves (STARTSEQ keeps the caller's)
        ctx = self.ctx_of(actor_e)
        exit_idx = [k for k, x in enumerate(ins_list) if x.op in (0x2B, 0xB6)]
        for kk, ins in enumerate(ins_list):
            if ins.off < s or ins.off >= e:
                continue
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
                        self.add("other", ctx); continue
                    src, typ, idx = wr
                    self.writes.append((src, typ, idx, actor_e if src == 2 else ei))
                    if src == 0:
                        GLOBW[(typ, idx)] += 1
                        near_exit = any(0 < j - kk <= 12 for j in exit_idx)
                        if near_exit and not (typ in (6, 7) and idx == 0):
                            EXITGLOBW[(typ, idx)] += 1
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
                        self.glob_reads.add((typ, idx)); self.reads["glob"] += 1
                    elif src == 1:
                        self.map_reads.add((typ, idx)); self.reads["map"] += 1
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
                        a = ins.args
                        ie = ins.arg_is_expr
                        if op == 0xAD:
                            a, ie = a[1:], ie[1:]
                        if op == 0xBF:
                            a, ie = a[1:], ie[1:]
                        if len(a) >= 2 and not ie[0] and not ie[1]:
                            if op in (0x23, 0xBF):
                                self.landings.append((op, s16(a[0]), None, s16(a[1])))
                            elif len(a) >= 3 and not ie[2]:
                                self.landings.append((op, s16(a[0]), s16(a[1]), s16(a[2])))
                        else:
                            self.landings.append((op, None, None, None))
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
            # calls
            if op in (0x10, 0x12, 0x14) and len(ins.args) >= 3:
                if ins.arg_is_expr[1]:
                    self.unresolved["expr-uid"] += 1; continue
                tgts, why = self.f.resolve_uid(ins.args[1], actor_e)
                tg = ins.args[2]
                if why:
                    self.unresolved[why] += 1
                for t in sorted(tgts):
                    if t in self.f.player:
                        self.player_calls.append((tag, tg, {0x10: "Async", 0x12: "RunScript", 0x14: "Sync"}[op]))
                    if self.f.func(t, tg) is None:
                        self.missing += 1; continue
                    self.walk(t, tg, None, sender=ei, actor=None, depth=depth + 1)
            elif op in (0x16, 0x18, 0x1A) and len(ins.args) >= 2:
                tg = ins.args[1]
                snd = {sender} if sender is not None else set(self.f.player)
                for t in sorted(snd):
                    if self.f.func(t, tg) is None:
                        self.missing += 1; continue
                    self.walk(t, tg, None, sender=ei, actor=None, depth=depth + 1)
            elif op == 0x43 and ins.args:
                if ins.arg_is_expr[0]:
                    self.unresolved["expr-seq"] += 1; continue
                t = ins.args[0]
                if 0 <= t < self.f.eb.entry_count and not self.f.eb.entry(t).empty and self.f.eb.entry(t).funcs:
                    self.walk(t, self.f.eb.entry(t).funcs[0].tag, None, sender=ei, actor=actor_e,
                              depth=depth + 1)
                else:
                    self.missing += 1
            elif op in (0x07, 0x08, 0x09) and ins.args:
                if ins.arg_is_expr[0]:
                    self.unresolved["expr-init"] += 1; continue
                t = ins.args[0]
                if 251 <= t < 255:
                    continue
                if self.f.func(t, 0) is not None:
                    self.walk(t, 0, None, sender=ei, actor=None, depth=depth + 1)

    def finish(self):
        """Split MAP/Instance writes into closure-private vs shared (read anywhere outside the closure)."""
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
                MAPW[(typ, idx, shared)] += 1
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


# ------------------------------------------------------------------ classification
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
    if any(l[0] in (0x23, 0xA2, 0xE8) for l in c.landings):
        return "walk"
    if any(l[0] in (0xA1, 0xAD, 0xBF) for l in c.landings):
        return "teleport"
    return "anim-only"


# ------------------------------------------------------------------ roots
def find_press_spans(fld: Field, ei, tag):
    """Forward spans guarded by a Confirm/Special press poll: `05 {..KEYON(mask&PRESS)..} 02 skip`."""
    ins = fld.instrs(ei, tag)
    out = []
    for i, x in enumerate(ins[:-1]):
        if x.op != 0x05:
            continue
        hit = False
        for w in fld.expr_info(ei, tag, x):
            for (k, m) in w["keys"]:
                if k in ("KEYON", "KEYON2") and m is not None and (m & (PRESS_BITS | CIRCLE)):
                    hit = True
        if not hit:
            continue
        j = ins[i + 1]
        if j.op == 0x02:
            t = jump_target(j)
            if t is not None and t > j.end:
                out.append((j.end, t))
    return out


def roots_of(fld: Field):
    eb = fld.eb
    roots = []
    for e in eb.entries:
        if e.empty or e.index == 0:
            continue
        kinds = fld.kind.get(e.index, set())
        isreg = bool(kinds & {"region", "region?"})
        isobj = bool(kinds & {"object", "object?"})
        tags = {f.tag for f in e.funcs}
        if 3 in tags and (isreg or isobj):
            roots.append(("QUAD" if isreg else "NPC", e.index, 3, None))
        if 8 in tags and (isreg or isobj):
            roots.append(("CARD", e.index, 8, None))
        if 2 in tags and (isreg or isobj):
            for sp in find_press_spans(fld, e.index, 2):
                roots.append(("TREAD-POLL", e.index, 2, sp))
        if 1 in tags:
            for sp in find_press_spans(fld, e.index, 1):
                roots.append(("LOOP-POLL", e.index, 1, sp))
    return roots


def root_gate(fld: Field, ei, tag, span):
    """What the ROOT function's own guards read before acting: usercontrol / glob / map / item / party."""
    g = set()
    for ins in fld.instrs(ei, tag):
        if span and not (ins.off < span[0]):
            break
        if ins.op != 0x05:
            continue
        for w in fld.expr_info(ei, tag, ins):
            if w["writes"]:
                continue
            for (src, typ, idx) in w["reads"]:
                if src == 1 and typ in (0, 1) and idx in BRACKET_READ_BITS:
                    continue                                  # the stock control-macro selectors
                if src == 0 and typ in (6, 7) and idx == 0:
                    g.add("scenario"); continue
                g.add({0: "glob", 1: "map", 2: "local", 3: "null"}[src])
            if 2 in w["sysv"]:
                g.add("usercontrol")
            if "B_HAVE_ITEM" in w["ops"]:
                g.add("item")
            if "B_PARTYCHK" in w["ops"]:
                g.add("party")
    return g


# ------------------------------------------------------------------ main
def load_names():
    names = {}
    p = WT / "reference" / "field-manifest.tsv"
    for line in p.read_text(encoding="utf-8").splitlines():
        parts = line.split("\t")
        if len(parts) >= 3 and parts[1].strip().isdigit():
            names.setdefault(int(parts[1]), parts[2].strip())
    return names


def run(json_out=None, limit=None):
    names = load_names()
    bundle = EventBundle()
    fids = sorted(FIELD_BY_ID)
    if limit:
        fids = fids[:limit]
    stats = Counter()
    by_kind_class = defaultdict(Counter)
    loco_kinds = Counter()
    reason_counts = defaultdict(Counter)
    gate_counts = defaultdict(Counter)
    rows = []
    for fid in fids:
        data = bundle.eb_for_id(fid)
        if not data:
            stats["no_eb"] += 1
            continue
        try:
            eb = EbScript.from_bytes(data)
            fld = Field(fid, eb)
        except Exception as ex:
            stats["parse_fail"] += 1
            continue
        stats["fields_scanned"] += 1
        rts = roots_of(fld)
        if rts:
            stats["fields_with_roots"] += 1
        for (rk, ei, tag, span) in rts:
            c = Closure(fld, ei)
            c.walk(ei, tag, span, sender=None, actor=None)
            c.finish()
            cls, reasons = classify(c)
            lk = loco_kind(c)
            gate = root_gate(fld, ei, tag, span)
            stats[f"roots_{rk}"] += 1
            by_kind_class[rk][cls] += 1
            for r in reasons:
                reason_counts[rk][r] += 1
            for g in gate:
                gate_counts[(rk, cls)][g] += 1
            if lk:
                loco_kinds[(rk, cls, lk)] += 1
            if c.decode_fail:
                stats["closure_decode_fail"] += 1
            if c.unresolved:
                stats[f"unresolved_{rk}"] += 1
            # order: did a window rise before the player first moved?
            order = None
            for (b, ctx) in c.seq:
                if b == "loco_player":
                    order = "move-first"; break
                if b == "window":
                    order = "window-first"; break
            rows.append({
                "fid": fid, "name": names.get(fid, "?"), "root": rk, "entry": ei, "tag": tag,
                "span": list(span) if span else None, "class": cls, "reasons": reasons, "loco": lk,
                "buckets": sorted(c.buckets()), "gate": sorted(gate),
                "unresolved": dict(c.unresolved), "missing": c.missing, "nodes": len(c.nodes),
                "player_calls": c.player_calls, "landings": c.landings[:40],
                "first_landing": c.landings[0] if c.landings else None,
                "keys": [(k, (hex(m) if m is not None else None), ctx) for (k, m, ctx) in c.keys][:8],
                "ladder_flag": c.ladder_flag, "loop": c.has_loop_player, "order": order,
                "windows_in_player": c.windows_in_player, "exit_targets": c.exit_targets,
                "glob_reads": sorted(c.glob_reads)[:8], "decode_fail": c.decode_fail,
                "kinds": sorted(fld.kind.get(ei, set())),
            })
    out = {"stats": dict(stats),
           "by_root_class": {k: dict(v.most_common()) for k, v in by_kind_class.items()},
           "reasons": {k: dict(v.most_common()) for k, v in reason_counts.items()},
           "loco_kinds": {"|".join(k): v for k, v in sorted(loco_kinds.items(), key=lambda kv: -kv[1])},
           "gates": {"|".join(k): dict(v.most_common()) for k, v in gate_counts.items()},
           "rows": rows,
           "mapw_top": [[t, i, sh, n] for (t, i, sh), n in MAPW.most_common(40)],
           "globw_top": [[t, i, n] for (t, i), n in GLOBW.most_common(40)],
           "exit_globw": [[t, i, n] for (t, i), n in EXITGLOBW.most_common(40)]}
    if json_out:
        Path(json_out).write_text(json.dumps(out, indent=1, default=list), encoding="utf-8")
    return out


def report(out):
    P = print
    s = out["stats"]
    P("=" * 90)
    P("PRESS-FIRED INTERACTION CENSUS -- every real FF9 field, English .eb, transitive effect sets")
    P("=" * 90)
    P(json.dumps(s, indent=0))
    for rk, cc in out["by_root_class"].items():
        tot = sum(cc.values())
        P(f"\n[{rk}] {tot} interactions")
        for cls, n in cc.items():
            P(f"    {cls:20s} {n:6d}  {100.0 * n / tot:5.1f}%")
        P(f"    reasons: {out['reasons'].get(rk)}")
    P("\nLOCOMOTION kinds (root|class|kind):")
    for k, v in out["loco_kinds"].items():
        P(f"    {k:55s} {v}")


if __name__ == "__main__":
    jout = sys.argv[sys.argv.index("--json") + 1] if "--json" in sys.argv else None
    lim = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
    o = run(jout, lim)
    report(o)
