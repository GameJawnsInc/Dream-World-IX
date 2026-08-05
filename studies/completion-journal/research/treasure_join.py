"""treasure_join.py -- v2, the REWARD-EVENT atlas generator (section 7.2 Q2).

v1 asked "what fraction of GRANT SITES join to a latch bit?" and answered 70.5%.
A six-agent adversarial pass measured that number against hand-disassembled bytes and
refuted it: **the grant site is not the unit and half the sites do not exist.** FF9's
compiler emits a four-arm reward macro (clamped-gil / item / card / literal-gil) and
specializes the selector to a literal ``SET(const 0|1)`` at compile time; the kit's
``FieldFlow`` does not constant-fold, so 1200 of v1's 2343 "grant sites" were
unreachable template arms -- and 100% latch-classified, because a dead arm sits inside
the once-guard by construction. The dead arms also carry MIRRORED JUNK payloads: an item
chest writes ``item_id - 1000`` into its dead ``AddGil`` (377 rows read as ~16.7M gil), a
gil chest writes ``gil + 1000`` into its dead ``AddItem`` (field 455's 135-gil chest owns
the junk id 1135).

**v2's unit is the REWARD EVENT, keyed on the latch bit** -- not the grant site, not the
field. Disc-variant rooms carrying the same bits (911/1911 Treno, 1102/1106 Cleyra) merge
into ONE event instead of double-counting.

What v2 does that v1 did not, each item measured in that pass:

1. CONSTANT-FOLD REACHABILITY. ``SET(<bare literal>) ; JMP_IF(NOT)`` decides its branch at
   compile time (engine-exact: ``EBin.cs`` beq/bne test the preceding expression's value).
   Only fold-live blocks may claim a grant, a latch write, or a gil amount.
2. THE INTER-PROCEDURAL CALLER JOIN. One shared dispatcher on the player entry absorbed
   most of v1's residue. Its protocol, decoded at field 1861 and byte-confirmed here:
   caller does ``Byte[226] = Bit[N]`` (read latch), ``Int16[224] = <literal reward code>``,
   ``RunScriptSync(2, uid, 12|13)``, then ``Bit[N] = Byte[226]`` (commit only if the grant
   landed). The callee's own ``AddItem({Int16[224]})`` is MECHANISM, not content -- v2
   classes those rows ``dispatcher`` and excludes them, and mines the CALL SITE instead.
   Reward-code encoding (the dispatcher's own branch tests confirm it): 0-255 item,
   256-511 key item, 512-611 card, >= 1000 gil with ``amount = code - 1000``, and the
   sentinel 29999 = "show the message, grant nothing" (74 of the 204 call sites; decoding
   it arithmetically mints 74 phantom 28,999-gil rewards).
   Two traps this join has to dodge, both proven on the corpus: GLOB ``Int16[220..227]`` is
   a SHARED scratch block that ordinary rooms also use for coordinates, so "assigns 224"
   identifies nothing -- the dispatcher is fingerprinted by READING 224 and MARKING
   ``Byte[226]`` with a literal (field 911's Stellazzio handler parks a coordinate in 224
   and was misread as the dispatcher, deleting all seven of its real latches).
3. THE WRITE SIDE ACCEPTS ``Bit[N] = <variable>``. v1 required ``value == 1``, which is
   exactly the form the indirect commit does NOT use (135 such writes corpus-wide).
4. THE SAME-FUNCTION WRITE FALLBACK v1's docstring promised but never implemented.
5. DOMINANCE-GATED WRITE SIDE (fixes F4, a proven LIVE false pairing). v1 took every bit
   write inside ``innermost_guard_block``'s region, so an UNGUARDED grant sitting at a
   macro's join label inherited the PREVIOUS chest's bit (field 600 joined
   ``AddItem(key item #32)`` to 7658/7659, two different neighbours, for one item). v2
   accepts a write only when its block DOMINATES the grant's block (or is the same block)
   -- the real ``if (bit==0) { bit=1; AddItem }`` shape always dominates.
6. THE CATCH-UP FILTER (F6). 48 of 332 live strong latch bits are story gates, not
   treasure; the dangerous ones are SCENARIO CATCH-UP flags that a ``Main_Init`` mass-sets
   under an ``SC >= N`` guard (bit 3818 at Gizamaluke: a journal reading it as "received
   key item #14" is TRUE for anyone who merely reached SC 3740). v2 DERIVES the idiom --
   a Main_Init region guarded by a ScenarioCounter ``>=``/``>`` test that sets
   ``_CATCHUP_MIN_BITS`` or more distinct bits -- and disqualifies every bit it finds,
   corpus-wide. No bit is hardcoded.
7. REAL GIL AMOUNTS. A live gil chest calls ``AddGi({Global.Int16[228]})``; the amount is
   the ``Int16[228] = const(X)`` write next to it, never the operand. Literal ``AddGil``
   above the party cap and literal ``AddItem`` ids >= 1000 are junk payload slots and are
   dropped.
8. F5 SPLIT-BIT REPORTING. When rows of one reward macro disagree about the bit, v2 records
   the disagreement on both events instead of silently picking one -- twice: over live rows
   ("does a live reward still split?") and over a live row against its dead 22-byte twin
   ("is that how the bad bit got in?"). BOTH COME BACK EMPTY on this corpus, as does
   ``bits_reachable_only_via_dead_code`` -- upgrades 1 and 5 close the class outright. A
   gate plants a synthetic split and requires the detector to fire, so the zero is a
   measurement and not an unexecuted check.
9. THE DIGEST RANKS BY DISTINCT LATCH EVENTS, not by grant-site verbosity. v1's top-20 put
   the same Treno room in slots 1 and 2 (911 and 1911 are one room) and gave slot 17 to a
   field with 18 "grants" and zero rewards.

Honest limits v2 does NOT fix, carried forward from the pass so nobody re-derives them:
the residue's ``bare`` class still contains the Chocobo Hot & Cold prize shops, Dr. Tot's
card top-up and the ``B_HAVE_ITEM(id)==0``-guarded key items -- all latch-less BY DESIGN,
and correctly excluded from a chest atlas because the INVENTORY is their latch. Treno's
key-item sales are priced at runtime, so their gil events carry ``amount: null`` (never
read that as zero). And an event outside every Treasure-Hunter band is flagged
``story_gate_suspect``, not resolved: v2 can prove the pairing, not the meaning.

Per-grant classes (a row-level diagnostic; the ATLAS unit is the event):
  latch        one bit on BOTH sides (guard tests it, a dominating write sets it)
  latch-write  one dominating write-side bit, no guard-side
  latch-guard  one guard-side bit nobody in the function writes -- weak
  latch-fallback  no region evidence, but the whole function writes exactly one bit
  indirect     joined at the CALL SITE of the shared reward dispatcher
  ambiguous    > 1 candidate on the deciding side
  sc-window    no latch, but a ScenarioCounter guard -- cutscene reward, windowed
  bare         no latch, no SC -- repeatable (shop / dig / top-up grants)
  unresolved   computed item operand outside the dispatcher protocol
  dispatcher   inside the shared reward subroutine -- mechanism, mined at the caller

Output: ``treasure_join.json`` next to this file (gitignored -- derived from the user's own
install, regenerable), holding the events, the LIVE grant rows only (dead template arms are
never written: a consumer that trusts their amounts inflates gil catastrophically), and the
per-field digest RANKED BY DISTINCT LATCH EVENTS.

Self-check gates run on every invocation (``--check`` runs them against an existing JSON
without rescanning). Each gate is a hand-verified fact from the measurement pass; a failure
means the join regressed, not that the gate is stale.

Run from ``ff9mapkit/`` (so the local package shadows any editable install):

    py ../studies/completion-journal/research/treasure_join.py
    py ../studies/completion-journal/research/treasure_join.py --check
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter, defaultdict

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(os.path.dirname(_HERE)))
for p in (os.path.join(_REPO, "ff9mapkit"), _REPO):
    if p not in sys.path:
        sys.path.insert(0, p)

from ff9mapkit.extract import EventBundle, ID_TO_EVT                      # noqa: E402
from ff9mapkit.eb import EbScript                                         # noqa: E402
from ff9mapkit.eb.cfg import (FieldFlow, OP_SET, OP_JMP_IF, OP_JMP_IFNOT,  # noqa: E402
                              jump_target, parse_set)
from ff9mapkit import forkreport as FR                                    # noqa: E402

ADD_ITEM_OP = 0x48
ADD_GIL_OP = 0xCE
CALL_OPS = frozenset({0x10, 0x12, 0x14, 0x16, 0x18, 0x1A})

# expression-token constants (mirrored from eb.cfg / eb.disasm -- byte-exact)
_T_CONST, _T_CONST4, _T_END = 0x7D, 0x7E, 0x7F
_T_VARFUNC = 0xD3

# Treasure-Hunter scoring, re-verified against EventState.cs:53-72 in the measurement pass:
# bytes 896-960 and 966-975 at 1 pt/bit, bytes 182-186 at 2 pts/bit (the chocograph band).
# NOTE both facts the raw bands do not tell you: bytes 961-965 (bits 7688-7727) are NOT
# scored yet hold 33 real chest latches, and the 2-pt band receives ZERO field-script
# writes. Treasure Hunter rank is a DISPLAY value, never a completion metric.
_TH_SINGLE = set(range(896 * 8, 961 * 8)) | set(range(966 * 8, 976 * 8))
_TH_DOUBLE = set(range(182 * 8, 187 * 8))
_TH_UNSCORED_GAP = set(range(961 * 8, 966 * 8))

# the shared reward dispatcher's three GLOB scratch slots (field 1861, byte-confirmed)
REWARD_ARG = 224          # Int16[224] = <reward code>       (caller -> dispatcher)
REWARD_LATCH = 226        # Byte[226]  = Bit[N] / Bit[N] = Byte[226]  (read + commit)
GIL_AMOUNT = 228          # Int16[228] = <gil amount>        (the value AddGi actually adds)

# reward-code bands (the dispatcher's own branch tests: >=1000 gil, <512 item, else card)
CODE_GIL_MIN = 1000
CODE_CARD_MIN = 512
CODE_CARD_MAX = 612       # code % 1000 >= 612 -> engine no-op (FF9Item_Add_Generic)
# the dispatcher's FIRST test is `Int16[224] == 29999` -> show the message, grant NOTHING.
# Read as gil it would mint 74 phantom 28,999-gil rewards, which is what an unguarded
# `code - 1000` decode does. Named, not silently swallowed.
CODE_MSG_ONLY = 29999

MOGNET_BAND = frozenset(range(8376, 8512))   # documented Mognet mail-lock band
GIL_CAP = FR.GIL_CAP                          # 9,999,999 -- the FF9 party-gil ceiling
JUNK_ITEM_MIN = 1000                          # a literal AddItem id >= 1000 is a junk slot
_CATCHUP_MIN_BITS = 3                         # distinct bits that make a Main_Init set a MASS set
# Live rows this close belong to ONE reward macro. Kept tight on purpose: the macro's
# `Received !` / `Received Card!` AddItem twins sit 22 bytes apart, while two DIFFERENT
# chests in the same handler sit 106-320 apart (field 1603 grants Exploda and Elixir 106
# bytes apart on two legitimately different bits -- a wide window calls that a split).
_SPLIT_CLUSTER_BYTES = 32
_CALL_LOOKAHEAD = 6                           # instrs after Int16[224]= that may hold the call

# classes whose rows are trusted to define a reward EVENT
EVENT_CLASSES = ("latch", "latch-write", "latch-fallback", "latch-guard", "indirect")


# ---------------------------------------------------------------------------
# byte-level helpers


def _imm(ins, i):
    """Literal operand i of a disasm Instr, or None when it is an expression."""
    if i >= len(ins.args) or (ins.arg_is_expr and ins.arg_is_expr[i]):
        return None
    v = ins.args[i]
    return int(v) if isinstance(v, int) else None


def _const_value(raw: bytes, ins):
    """The literal value of a SET that is exactly one constant (``05 7D lo hi 7F``), else None.

    This is the reward macro's payload-type selector -- the whole reason v1 counted dead code.
    """
    if ins.op != OP_SET:
        return None
    pos, limit = ins.off + 1, ins.end
    if pos >= limit:
        return None
    o = raw[pos]
    if o == _T_CONST and pos + 4 <= limit:
        v = raw[pos + 1] | (raw[pos + 2] << 8)
        if v >= 0x8000:
            v -= 0x10000
        return v if raw[pos + 3] == _T_END else None
    if o == _T_CONST4 and pos + 6 <= limit:
        v = (raw[pos + 1] | (raw[pos + 2] << 8) | (raw[pos + 3] << 16) | (raw[pos + 4] << 24))
        return v if raw[pos + 5] == _T_END else None
    return None


def folded_reach(fl, raw: bytes) -> set:
    """Block indices reachable from the function entry with const-only branches FOLDED.

    ``FuncFlow`` treats both successors of a ``JMP_IF(NOT)`` as reachable; when the deciding
    expression is a bare literal the engine takes exactly one of them. Reused verbatim from
    the audit's ``constfold.folded_reach``.
    """
    seen = {fl.entry}
    stack = [fl.entry]
    while stack:
        b = stack.pop()
        blk = fl.blocks[b]
        term = blk.instrs[-1] if blk.instrs else None
        cv = None
        if term is not None and term.op in (OP_JMP_IFNOT, OP_JMP_IF) and len(blk.instrs) >= 2:
            cv = _const_value(raw, blk.instrs[-2])
        succs = [s for s, _c in blk.succs]
        if cv is not None and term is not None and len(succs) == 2:
            tb = fl.block_at(jump_target(term))
            fall = fl.block_at(term.end)
            if term.op == OP_JMP_IFNOT:
                take = tb if cv == 0 else fall
            else:
                take = tb if cv != 0 else fall
            if take is not None:
                succs = [take]
        for s in succs:
            if s is not None and s not in seen:
                seen.add(s)
                stack.append(s)
    return seen


def var_refs(raw: bytes, ins):
    """Every ``(source, vtype, index)`` variable token inside a SET statement.

    ``parse_set`` reports the DESTINATION and (for simple assigns) a literal value; the
    indirect protocol needs the operands too -- ``Byte[226] = Bit[N]`` names its bit only
    in the expression. The walk is byte-exact with ``parse_expr_conds``.
    """
    pos, limit = ins.off + 1, ins.end
    out = []
    while pos < limit:
        o = raw[pos]
        pos += 1
        if o == _T_VARFUNC:
            pos += 3
            continue
        if o == _T_CONST:
            pos += 2
            continue
        if o == _T_CONST4:
            pos += 4
            continue
        if o >= 0xE0:
            if pos + 2 > limit:
                break
            out.append((o & 3, (o >> 2) & 7, raw[pos] | (raw[pos + 1] << 8)))
            pos += 2
            continue
        if o >= 0xC0:
            if pos + 1 > limit:
                break
            out.append((o & 3, (o >> 2) & 7, raw[pos]))
            pos += 1
            continue
        if o in (0x29, 0x5F, 0x79, 0x7A):
            pos += 1
            continue
        if o == 0x78:
            pos += 2
            continue
        if o == _T_END:
            break
    return out


def item_pool(iid: int) -> str:
    """``regular`` / ``key`` / ``card``, by the engine's ``id % 1000`` pool decode.

    A catalog needs this: a key item and a card are different journal columns and resolve
    their display names from different runtime tables (and the owner's install stacks
    Moguri, so no name may ever be baked in).
    """
    m = int(iid) % 1000
    return "card" if m >= CODE_CARD_MIN else "key" if m >= FR.REGULAR_MAX else "regular"


def decode_reward_code(code: int):
    """The dispatcher's 16-bit reward code -> a reward dict, or None when it grants nothing.

    Byte-confirmed against the dispatcher's own branch tests (field 1861 e18 tag 12):
    ``i16[224] >= 1000`` -> gil arm (``i16[228] = i16[224] - 1000``); ``< 512`` -> item arm;
    otherwise the card arm. 0-255 regular item, 256-511 key item, 512-611 card.
    """
    if code is None or code < 0 or code == CODE_MSG_ONLY:
        return None
    if code >= CODE_GIL_MIN:
        amt = code - CODE_GIL_MIN
        return {"kind": "gil", "id": None, "amount": amt} if amt > 0 else None
    if code % 1000 >= CODE_CARD_MAX:
        return None                                   # engine no-op
    if code == FR.NO_ITEM or FR.item_inert(code):
        return None
    return {"kind": "item", "id": code, "amount": None, "pool": item_pool(code),
            "label": FR.item_label(code)}


def _load_names() -> dict:
    """field id -> room name from reference/field-manifest.tsv (index != field id)."""
    names: dict = {}
    path = os.path.join(_REPO, "reference", "field-manifest.tsv")
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                parts = line.rstrip("\n").split("\t")
                if len(parts) < 3:
                    continue
                try:
                    fid = int(parts[1])
                except ValueError:
                    continue
                names.setdefault(fid, parts[2])
    except OSError:
        pass
    return names


# ---------------------------------------------------------------------------
# per-function analysis


class FuncScan:
    """One function's fold-live view: the facts every join in v2 is allowed to use."""

    __slots__ = ("key", "tag", "fl", "raw", "live", "bit_writes", "gil_consts",
                 "reads_226", "commits_226", "reads_224", "marks_226", "has_computed_grant")

    def __init__(self, key, tag, fl, raw):
        self.key = key
        self.tag = tag
        self.fl = fl
        self.raw = raw
        self.live = folded_reach(fl, raw)
        self.bit_writes = []        # [(off, block, bit)] -- Bit[N]=1 or Bit[N]=<var>, fold-live
        self.gil_consts = []        # [(off, block, value)] -- Int16[228] = const, fold-live
        self.reads_226 = []         # [(off, block, [bits])] -- Byte[226] = Bit[N]  (CALLER)
        self.commits_226 = []       # [(off, block, bit)]    -- Bit[N] = Byte[226]   (CALLER)
        self.reads_224 = False      # Int16[224] used as a SOURCE                    (CALLEE)
        self.marks_226 = False      # Byte[226] = <literal> -- "the grant landed"     (CALLEE)
        self.has_computed_grant = False
        self._scan()

    def _scan(self):
        raw = self.raw
        for blk in self.fl.blocks:
            b = blk.index
            if self.fl._dom[b] == 0:
                continue
            live = b in self.live
            for ins in blk.instrs:
                if ins.op in (ADD_ITEM_OP, ADD_GIL_OP):
                    if live and _imm(ins, 0) is None:
                        self.has_computed_grant = True
                    continue
                if ins.op != OP_SET:
                    continue
                st = parse_set(raw, ins)
                # -- callee fingerprint. GLOB Int16[220..227] is a SHARED scratch block (the
                # same field also stores coordinates there), so "assigns 224" proves nothing;
                # only READING 224 as a source and MARKING Byte[226] with a literal do.
                refs = var_refs(raw, ins)
                n224 = sum(1 for s, v, i in refs
                           if s == 0 and v in (6, 7) and i == REWARD_ARG)
                dst224 = (st.kind == "assign" and st.source == 0 and st.vtype in (6, 7)
                          and st.index == REWARD_ARG)
                if n224 and not (dst224 and n224 == 1):
                    self.reads_224 = True
                if st.kind == "assign" and st.source == 0 and st.vtype in (4, 5) \
                        and st.index == REWARD_LATCH and st.value is not None:
                    self.marks_226 = True
                if not live or st.kind != "assign" or st.source != 0:
                    continue
                if st.vtype in (0, 1):
                    # v2 accepts the computed commit form Bit[N] = <variable> (upgrade 3);
                    # Bit[N] = 0 is a CLEAR and compound ops are not latches.
                    if st.value == 1 or (st.value is None and st.pure):
                        self.bit_writes.append((ins.off, b, st.index))
                        if st.value is None and any(s == 0 and v in (4, 5)
                                                    and i == REWARD_LATCH for s, v, i in refs):
                            self.commits_226.append((ins.off, b, st.index))
                elif st.vtype in (4, 5) and st.index == REWARD_LATCH and st.value is None:
                    bits = [i for s, v, i in refs if s == 0 and v in (0, 1)]
                    if bits:
                        self.reads_226.append((ins.off, b, bits))
                elif st.vtype in (6, 7) and st.index == GIL_AMOUNT and st.value is not None:
                    self.gil_consts.append((ins.off, b, st.value))

    # -- queries used by the join -------------------------------------------

    @property
    def is_dispatcher(self) -> bool:
        """The shared reward subroutine -- the CALLEE half of the protocol.

        Its fingerprint (byte-confirmed at field 1861 e18 tag 12): a computed
        ``AddItem``/``AddGi``, a branch that READS ``Int16[224]``, and a literal
        ``Byte[226] = 1`` "the grant landed" mark. A caller does the mirror image
        (``Byte[226] = Bit[N]`` computed, ``Int16[224] = <literal>``) and is NOT a
        dispatcher -- nor is an ordinary chest room that happens to park a coordinate in
        the shared 220-227 scratch block (field 911's Stellazzio handler does exactly that).
        """
        return self.has_computed_grant and self.reads_224 and self.marks_226

    def dominating_writes(self, b: int) -> set:
        """Bits written by a fold-live block that DOMINATES *b* (``_dom`` includes b itself).

        This is the F4 fix: a write in a SIBLING arm of the same guarded region never
        happened on the path that reaches the grant, so it may not claim it.
        """
        mask = self.fl._dom[b]
        return {bit for _off, wb, bit in self.bit_writes if (mask >> wb) & 1}

    def func_writes(self) -> set:
        return {bit for _off, _wb, bit in self.bit_writes}

    @property
    def is_mognet_handler(self) -> bool:
        """The shared moogle/Mognet mail handler: one ``AddItem`` behind a 64-way unrolled
        scan of mail bits 8440-8503. v1 reported its 58 clones as 58 independent
        ``ambiguous`` rows, overstating the residue's diversity by an order of magnitude.
        v2's dominance rule drops them to ``bare`` (no arm's write dominates the shared
        join) -- correct for a chest atlas, so label them rather than lose them."""
        return any(bit in MOGNET_BAND for _off, _wb, bit in self.bit_writes)

    def gil_amount_at(self, off: int, b: int):
        """The ``Int16[228] = const`` nearest ABOVE *off* on a dominating path (upgrade 7)."""
        mask = self.fl._dom[b]
        best = None
        for woff, wb, val in self.gil_consts:
            if woff < off and (mask >> wb) & 1 and (best is None or woff > best[0]):
                best = (woff, val)
        return None if best is None else best[1]


# ---------------------------------------------------------------------------
# the joins


def _guard_bits(fl, b, ctx_bits):
    """Bits proven ``== 0`` on the way into block *b* (raw dominator chain + caller context)."""
    out = set(ctx_bits)
    for _d, conds in fl._raw_guards(b):
        for c in conds:
            if c.is_glob_bit and c.cmp == "==" and c.value == 0:
                out.add(c.index)
    return out


def join_direct(fs: FuncScan, b: int, off: int, ctx_bits, ctx_sc):
    """Classify one literal grant. Returns ``(cls, latch)``."""
    fl = fs.fl
    guard = _guard_bits(fl, b, ctx_bits)
    writes = fs.dominating_writes(b)
    both = guard & writes
    if len(both) == 1:
        return "latch", next(iter(both))
    if len(both) > 1:
        return "ambiguous", sorted(both)
    if len(writes) == 1:
        return "latch-write", next(iter(writes))
    if len(writes) > 1:
        return "ambiguous", sorted(writes)
    if len(guard) == 1:
        gb = next(iter(guard))
        # a guard-side-only bit is only a latch if somebody in the function actually sets it
        return ("latch", gb) if gb in fs.func_writes() else ("latch-guard", gb)
    if len(guard) > 1:
        return "ambiguous", sorted(guard)
    # upgrade 4: the same-function fallback v1's docstring promised and never implemented
    fw = fs.func_writes()
    if len(fw) == 1:
        return "latch-fallback", next(iter(fw))
    r = fl.guards_at_ex(off)
    live_conds = list(r[0]) if r else []
    if ctx_sc or any(c.is_scenario for c in live_conds):
        return "sc-window", None
    return "bare", None


def join_indirect(fs: FuncScan, b: int, call_off: int, ctx_bits):
    """The caller-side latch for one shared-dispatcher call site (upgrade 2).

    The protocol brackets the call: ``Byte[226] = Bit[N]`` immediately above it and
    ``Bit[N] = Byte[226]`` immediately below. Take the nearest of each and require them to
    agree; fall back to whichever exists, then to a dominator-chain guard bit.
    """
    read = None
    for off, _wb, bits in fs.reads_226:
        if off < call_off and len(bits) == 1 and (read is None or off > read[0]):
            read = (off, bits[0])
    commit = None
    for off, _wb, bit in fs.commits_226:
        if off > call_off and (commit is None or off < commit[0]):
            commit = (off, bit)
    if read is not None and commit is not None:
        if read[1] == commit[1]:
            return "indirect", read[1]
        return "indirect-split", sorted({read[1], commit[1]})
    if commit is not None:
        return "indirect", commit[1]
    if read is not None:
        return "indirect", read[1]
    guard = _guard_bits(fs.fl, b, ctx_bits)
    if len(guard) == 1:
        return "indirect", next(iter(guard))
    if len(guard) > 1:
        return "indirect-ambiguous", sorted(guard)
    return "indirect-bare", None


def catchup_bits(eb, scans):
    """``(catchup, main_init_written)`` -- upgrade 6 and its softer sibling.

    ``catchup`` = bits a ``Main_Init`` MASS-SETS under a ``ScenarioCounter >= N`` guard.
    The idiom is derived, never hardcoded: field 706's Main_Init runs
    ``SC >= 3740 && Bit[3816] == 0`` and then sets 3816,3817,3818,3819,3823,3825-3831 in one
    straight line. Any bit reachable that way is a SCENARIO CATCH-UP flag -- true for a
    player who merely advanced the story -- so it can never mean "the player collected this".
    These are EXCLUDED from the atlas.

    ``main_init_written`` = every bit any Main_Init writes at all. The audit's blunter
    recommendation was to disqualify all of them; that over-excludes (a room's Init may
    legitimately touch a chest bit), so v2 FLAGS them on the event and lets the catalog
    author adjudicate.
    """
    out = set()
    init_written = set()
    for (ei, fi), fs in scans.items():
        if ei != 0 or fs.tag not in (0, 10):
            continue
        init_written |= fs.func_writes()
        fl = fs.fl
        roots = set()
        for blk in fl.blocks:
            b = blk.index
            if b not in fs.live or fl._dom[b] == 0:
                continue
            sc_ge = False
            for _d, conds in fl._raw_guards(b):
                for c in conds:
                    if c.is_scenario and c.cmp in (">=", ">"):
                        sc_ge = True
            if not sc_ge:
                continue
            root = fl.innermost_guard_block(b)
            roots.add(b if root is None else root)
        for root in roots:
            region = {x for x in fl.dominated_by(root) if x in fs.live}
            bits = {bit for _off, wb, bit in fs.bit_writes if wb in region}
            if len(bits) >= _CATCHUP_MIN_BITS:
                out |= bits
    return out, init_written


# ---------------------------------------------------------------------------
# the scan


def scan_corpus():
    bundle = EventBundle()
    grants: list = []
    dead_rows: Counter = Counter()
    stats: Counter = Counter()
    junk: Counter = Counter()
    catchup: set = set()
    main_init_bits: set = set()
    dead_bits: dict = defaultdict(set)      # bit -> {fields} seen ONLY in dead arms
    live_bits: set = set()
    arm_rows: list = []                     # dead template arms that still name a bit (F5)

    for fid in sorted(ID_TO_EVT):
        try:
            data = bundle.eb_for_id(fid)
            if not data:
                continue
            eb = EbScript.from_bytes(data)
        except Exception:
            stats["fields_unreadable"] += 1
            continue
        stats["fields_scanned"] += 1
        try:
            ff = FieldFlow.build(eb)
        except Exception:
            stats["fields_flow_failed"] += 1
            continue
        raw = eb.data

        scans = {}
        for key, fl in ff.flows.items():
            ei, fi = key
            scans[key] = FuncScan(key, eb.entries[ei].funcs[fi].tag, fl, raw)
        _cu, _mi = catchup_bits(eb, scans)
        catchup |= _cu
        main_init_bits |= _mi

        for key, fs in scans.items():
            ei, fi = key
            ftag = fs.tag
            fl = fs.fl
            ctx = ff.ctx.get(key, {})
            # caveat 11: only EXECUTION-time context (armed=False) may prove a guard;
            # an arming-time condition held when the handler was installed, not when it ran.
            ctx_bits = {c.index for c, armed in ctx.items()
                        if not armed and c.is_glob_bit and c.cmp == "==" and c.value == 0}
            ctx_sc = any(c.is_scenario for c in ctx)
            dispatcher = fs.is_dispatcher

            for blk in fl.blocks:
                b = blk.index
                if fl._dom[b] == 0:
                    continue                                # structurally unreachable
                live = b in fs.live
                for idx, ins in enumerate(blk.instrs):
                    row = None
                    if ins.op == ADD_ITEM_OP:
                        iid = _imm(ins, 0)
                        if iid is None:
                            if not live:
                                dead_rows["item-computed"] += 1
                                continue
                            if dispatcher:
                                stats["dispatcher"] += 1
                                continue
                            stats["unresolved"] += 1
                            u = {"field": fid, "entry": ei, "func": ftag, "off": ins.off,
                                 "kind": "item", "id": None, "cls": "unresolved",
                                 "latch": None}
                            if fs.is_mognet_handler:
                                u["mognet_handler"] = True
                            grants.append(u)
                            continue
                        if iid == FR.NO_ITEM or FR.item_inert(iid):
                            continue                        # engine no-op, not a grant
                        if iid >= JUNK_ITEM_MIN:
                            # upgrade 7: the mirrored junk slot of a GIL chest (gil + 1000)
                            junk["item_id_ge_1000" + ("_LIVE" if live else "")] += 1
                            continue
                        row = {"kind": "item", "id": iid, "count": _imm(ins, 1),
                               "pool": item_pool(iid), "label": FR.item_label(iid),
                               "amount": None}
                    elif ins.op == ADD_GIL_OP:
                        amt = _imm(ins, 0)
                        if amt is not None and amt > GIL_CAP:
                            # the mirrored junk slot of an ITEM chest (item_id - 1000)
                            junk["gil_above_cap" + ("_LIVE" if live else "")] += 1
                            continue
                        if not live:
                            dead_rows["gil"] += 1
                            continue
                        if dispatcher:
                            stats["dispatcher"] += 1
                            continue
                        if amt is None:
                            amt = fs.gil_amount_at(ins.off, b)   # upgrade 7: Int16[228]
                            if amt is None:
                                junk["gil_amount_unknown"] += 1
                        row = {"kind": "gil", "id": None, "amount": amt}
                    elif ins.op == OP_SET and live and not dispatcher:
                        # upgrade 2: an indirect reward CALL SITE
                        st = parse_set(raw, ins)
                        if not (st.kind == "assign" and st.source == 0
                                and st.vtype in (6, 7) and st.index == REWARD_ARG
                                and st.value is not None):
                            continue
                        if not any(nx.op in CALL_OPS
                                   for nx in blk.instrs[idx + 1:idx + 1 + _CALL_LOOKAHEAD]):
                            continue
                        stats["indirect_call_sites"] += 1
                        rw = decode_reward_code(st.value)
                        if rw is None:
                            stats["indirect_code_inert"] += 1
                            continue
                        cls, latch = join_indirect(fs, b, ins.off, ctx_bits)
                        stats[cls] += 1
                        g = dict(rw)
                        g.update({"field": fid, "entry": ei, "func": ftag, "off": ins.off,
                                  "cls": cls, "latch": latch, "code": st.value})
                        if isinstance(latch, int):
                            g["th"] = (2 if latch in _TH_DOUBLE
                                       else 1 if latch in _TH_SINGLE else 0)
                            live_bits.add(latch)
                        grants.append(g)
                        continue
                    else:
                        continue

                    if row is not None and row["kind"] == "item" and not live:
                        dead_rows["item"] += 1
                    if not live:
                        # a dead arm still names a bit; record which bits ONLY dead code
                        # claims, and keep a light row so the F5 detector has both sides
                        _cls_d, latch_d = join_direct(fs, b, ins.off, ctx_bits, ctx_sc)
                        if isinstance(latch_d, int):
                            dead_bits[latch_d].add(fid)
                            arm_rows.append({"field": fid, "entry": ei, "func": ftag,
                                             "off": ins.off, "latch": latch_d, "live": False,
                                             "label": row.get("label"),
                                             "amount": row.get("amount")})
                        continue
                    if dispatcher:
                        stats["dispatcher"] += 1
                        continue

                    cls, latch = join_direct(fs, b, ins.off, ctx_bits, ctx_sc)
                    stats[cls] += 1
                    row.update({"field": fid, "entry": ei, "func": ftag, "off": ins.off,
                                "cls": cls, "latch": latch})
                    if isinstance(latch, int):
                        row["th"] = (2 if latch in _TH_DOUBLE
                                     else 1 if latch in _TH_SINGLE else 0)
                        live_bits.add(latch)
                    elif fs.is_mognet_handler:
                        row["mognet_handler"] = True
                        stats["residue_in_mognet_handler"] += 1
                    grants.append(row)

    return {"grants": grants, "stats": stats, "junk": junk, "dead_rows": dead_rows,
            "catchup": catchup, "arm_rows": arm_rows,
            "main_init_bits": main_init_bits,
            "dead_only_bits": sorted(b for b in dead_bits if b not in live_bits)}


# ---------------------------------------------------------------------------
# events (the atlas unit)


def split_bit_clusters(rows, width=_SPLIT_CLUSTER_BYTES, require_dead=False):
    """F5: rows of ONE reward macro that disagree about the latch bit.

    Reported, never silently resolved -- v1's classifier picked whichever bit the
    surrounding block happened to contain (field 2803 put the item rows on 7360 and the gil
    row on 2969, the Hammer-trade quest gate).

    Two calls, two questions. ``require_dead=False`` asks "do two LIVE rows of one macro
    disagree?"; ``require_dead=True`` asks the sharper one -- "does a DEAD template arm
    name a different bit than the live twin 22 bytes away?", which is how F5's measured
    population (2803's gil row on the Hammer-trade gate, 2259's on the Stiltzkin purchase
    flag) entered v1's atlas in the first place.
    """
    by_func = defaultdict(list)
    for g in rows:
        if isinstance(g.get("latch"), int):
            by_func[(g["field"], g["entry"], g["func"])].append(g)
    out = []
    for k, group in by_func.items():
        group.sort(key=lambda r: r["off"])
        cluster = [group[0]]
        for r in group[1:]:
            if r["off"] - cluster[-1]["off"] <= width:
                cluster.append(r)
            else:
                out.extend(_emit_split(k, cluster, require_dead))
                cluster = [r]
        out.extend(_emit_split(k, cluster, require_dead))
    return out


def _emit_split(key, cluster, require_dead):
    bits = sorted({r["latch"] for r in cluster})
    if len(bits) < 2:
        return []
    if require_dead and not (any(not r.get("live", True) for r in cluster)
                             and any(r.get("live", True) for r in cluster)):
        return []
    return [{"field": key[0], "entry": key[1], "func": key[2], "bits": bits,
             "offs": [r["off"] for r in cluster],
             "live": [bool(r.get("live", True)) for r in cluster],
             "rewards": [r.get("label") or ("%s gil" % r.get("amount")) for r in cluster]}]


def build_events(grants, names, catchup, main_init_bits):
    """Group LIVE, latched grants into reward EVENTS keyed on the latch bit (upgrade 5)."""
    splits = {}
    for s in split_bit_clusters(grants):
        for bit in s["bits"]:
            splits.setdefault(bit, []).append(s)

    events: dict = {}
    excluded = {"catchup": defaultdict(set), "mognet": defaultdict(set)}
    for g in grants:
        bit = g.get("latch")
        if not isinstance(bit, int) or g["cls"] not in EVENT_CLASSES:
            continue
        if bit in catchup:
            excluded["catchup"][bit].add(g["field"])
            continue
        if bit in MOGNET_BAND:
            excluded["mognet"][bit].add(g["field"])
            continue
        ev = events.get(bit)
        if ev is None:
            ev = events[bit] = {
                "bit": bit,
                "th": 2 if bit in _TH_DOUBLE else 1 if bit in _TH_SINGLE else 0,
                "th_band": ("2pt" if bit in _TH_DOUBLE else "1pt" if bit in _TH_SINGLE
                            else "unscored-gap" if bit in _TH_UNSCORED_GAP else "outside"),
                "fields": set(), "rewards": {}, "sites": 0, "classes": Counter(),
            }
        ev["fields"].add(g["field"])
        ev["sites"] += 1
        ev["classes"][g["cls"]] += 1
        if g["kind"] == "item":
            ev["rewards"][("item", g["id"])] = {"kind": "item", "id": g["id"],
                                                "pool": g.get("pool"),
                                                "label": g.get("label")}
        else:
            ev["rewards"][("gil", g.get("amount"))] = {"kind": "gil",
                                                       "amount": g.get("amount")}

    out = []
    for bit, ev in sorted(events.items()):
        fields = sorted(ev["fields"])
        rewards = [ev["rewards"][k] for k in sorted(ev["rewards"], key=lambda t: (t[0], t[1] or 0))]
        row = {"bit": bit, "th": ev["th"], "th_band": ev["th_band"],
               "fields": fields, "names": [names.get(f, "?") for f in fields],
               "rewards": rewards, "sites": ev["sites"],
               "classes": dict(sorted(ev["classes"].items()))}
        if any(r["kind"] == "gil" and r.get("amount") is None for r in rewards):
            # a runtime-priced grant (Treno's key-item sales haggle the price). NULL is the
            # honest answer -- a consumer must never read it as zero.
            row["amount_unknown"] = True
        if len(rewards) > 1:
            row["multi_payload"] = True          # F7: one bit, several ids (or a gil twin)
        if len(fields) > 1:
            row["disc_variants"] = True          # the 911/1911 merge this keying exists for
        if ev["th_band"] == "outside":
            # F6: a latch outside every Treasure-Hunter band is a story/quest gate until a
            # human says otherwise (2101 = Ramuh's quiz, 3793 = Brahne's play-score gift).
            row["story_gate_suspect"] = True
        if bit in main_init_bits:
            # some field's Main_Init writes this bit -- it can fire without the player ever
            # reaching the grant. Flagged, not excluded (the mass-set class already is).
            row["main_init_written"] = True
        if bit in splits:
            row["split_bit"] = sorted({b for s in splits[bit] for b in s["bits"]})
        out.append(row)
    return out, {k: {str(b): sorted(f) for b, f in v.items()} for k, v in excluded.items()}


# ---------------------------------------------------------------------------
# gates -- every one is a hand-verified fact from the measurement pass


_F706_CHESTS = {"Elixir", "Extension", "AlohaTshirt", "PhoenixPinion", "Tent", "Ether"}
_ICE_CAVERN_FIELDS = range(300, 313)
_ICE_CAVERN_BITS = set(range(7264, 7272))
_GIL_SANE_MAX = 100_000


def _field_events(events, fid):
    return [e for e in events if fid in e["fields"]]


def run_gates(out) -> list:
    """Hard self-checks. Returns ``[(name, ok, detail)]``; every failure is a real regression."""
    events = out["events"]
    res = []

    labels = {r["label"] for e in _field_events(events, 706) for r in e["rewards"]
              if r["kind"] == "item" and r.get("label")}
    res.append(("f706-gizamaluke-six-chests", labels == _F706_CHESTS,
                "items=%s" % sorted(labels)))

    ice = [e for e in events if any(f in _ICE_CAVERN_FIELDS for f in e["fields"])]
    ice_bits = {e["bit"] for e in ice}
    ice_fields = {f for e in ice for f in e["fields"] if f in _ICE_CAVERN_FIELDS}
    res.append(("ice-cavern-contiguous-7264-7271",
                ice_bits == _ICE_CAVERN_BITS and len(ice_fields) == 4,
                "bits=%s fields=%s" % (sorted(ice_bits), sorted(ice_fields))))

    big = [(e["bit"], r["amount"]) for e in events for r in e["rewards"]
           if r["kind"] == "gil" and (r.get("amount") or 0) > _GIL_SANE_MAX]
    res.append(("no-gil-event-above-100k", not big, "offenders=%s" % big[:5]))

    res.append(("bit-3818-catchup-excluded",
                not any(e["bit"] == 3818 for e in events),
                "3818 in derived catch-up set: %s" % (3818 in set(out["catchup_bits"]))))

    b911 = {e["bit"] for e in _field_events(events, 911)}
    b1911 = {e["bit"] for e in _field_events(events, 1911)}
    merged = all(sorted(e["fields"]) == [911, 1911]
                 for e in events if e["bit"] in (b911 | b1911))
    res.append(("treno-911-1911-one-event-set",
                bool(b911) and b911 == b1911 and merged,
                "911=%s 1911=%s merged=%s" % (sorted(b911), sorted(b1911), merged)))

    # Both F5 reports come back empty on this corpus. A check that cannot fail is not a
    # check -- so break the detector on purpose and require it to fire.
    probe = split_bit_clusters([
        {"field": 0, "entry": 0, "func": 0, "off": 100, "latch": 11, "live": True},
        {"field": 0, "entry": 0, "func": 0, "off": 122, "latch": 22, "live": False},
    ], require_dead=True)
    res.append(("split-detector-fires-on-a-planted-split", len(probe) == 1,
                "planted twin -> %d cluster(s); corpus reports %d live / %d dead-twin"
                % (len(probe), len(out["split_bit_sites"]),
                   len(out["split_bit_sites_dead_arm_twins"]))))

    ev = next((e for e in events if e["bit"] == 7648), None)
    ok = bool(ev) and 600 in ev["fields"] \
        and any(r["kind"] == "gil" and r.get("amount") == 5000 for r in ev["rewards"]) \
        and not any(r["kind"] == "item" and r.get("id", 0) >= 1000 for r in ev["rewards"])
    res.append(("f600-bit-7648-live-arm-is-5000-gil", ok,
                "event=%s" % (ev["rewards"] if ev else None)))

    return res


# ---------------------------------------------------------------------------


def main(argv) -> int:
    dest = os.path.join(_HERE, "treasure_join.json")
    names = _load_names()

    if "--check" in argv:
        with open(dest, encoding="utf-8") as fh:
            out = json.load(fh)
    else:
        scanned = scan_corpus()
        grants = scanned["grants"]
        catchup = scanned["catchup"]
        events, excluded = build_events(grants, names, catchup,
                                        scanned["main_init_bits"])
        stats = scanned["stats"]

        ev_fields = defaultdict(int)
        for e in events:
            for f in e["fields"]:
                ev_fields[f] += 1
        live_sites = Counter(g["field"] for g in grants)

        cls_counts = Counter(g["cls"] for g in grants)
        th_counts = Counter(e["th_band"] for e in events)
        out = {
            "generator": "studies/completion-journal/research/treasure_join.py (v2)",
            "unit": "reward EVENT keyed on the latch bit (disc-variant fields merged)",
            "engine_truth": {
                "th_bytes_1pt": "896-960, 966-975 (EventState.cs:53-72)",
                "th_bytes_2pt": "182-186 -- the chocograph band; ZERO field-script writes",
                "th_unscored_gap": "961-965 (bits 7688-7727) -- unscored, holds real chests",
                "treasure_hunter_is_not_a_completion_metric": True,
                "reward_code": "0-255 item, 256-511 key item, 512-611 card, >=1000 gil (code-1000)",
            },
            "stats": dict(sorted(stats.items())),
            "row_classes": dict(sorted(cls_counts.items())),
            "dead_rows_folded_out": dict(sorted(scanned["dead_rows"].items())),
            "junk_payload_rows_dropped": dict(sorted(scanned["junk"].items())),
            "summary": {
                "fields_scanned": stats["fields_scanned"],
                "live_grant_rows": len(grants),
                "dead_template_rows_excluded": sum(scanned["dead_rows"].values()),
                "reward_events": len(events),
                "distinct_latch_bits": len(events),
                "events_th_1pt": th_counts.get("1pt", 0),
                "events_th_unscored_gap": th_counts.get("unscored-gap", 0),
                "events_outside_th_bands": th_counts.get("outside", 0),
                "events_merging_disc_variants": sum(1 for e in events if e.get("disc_variants")),
                "events_multi_payload": sum(1 for e in events if e.get("multi_payload")),
                "events_split_bit_reported": sum(1 for e in events if e.get("split_bit")),
                "split_bit_dead_arm_twin_disagreements": len(split_bit_clusters(
                    grants + scanned["arm_rows"], require_dead=True)),
                "indirect_events": sum(1 for e in events if "indirect" in e["classes"]),
                "indirect_call_sites": stats.get("indirect_call_sites", 0),
                "indirect_joins_resolved": cls_counts.get("indirect", 0),
                "dispatcher_rows_excluded": stats.get("dispatcher", 0),
                "catchup_bits_derived": len(catchup),
                "events_excluded_catchup": len(excluded["catchup"]),
                "events_excluded_mognet": len(excluded["mognet"]),
                "events_story_gate_suspect": sum(1 for e in events
                                                 if e.get("story_gate_suspect")),
                "events_main_init_written": sum(1 for e in events
                                                if e.get("main_init_written")),
                "bits_reachable_only_via_dead_code": len(scanned["dead_only_bits"]),
                "indirect_msg_only_sentinel_rows": stats.get("indirect_code_inert", 0),
                "residue_unresolved": cls_counts.get("unresolved", 0),
                "residue_bare": cls_counts.get("bare", 0),
                "residue_sc_window": cls_counts.get("sc-window", 0),
                "residue_ambiguous": cls_counts.get("ambiguous", 0),
                "residue_in_mognet_handler": stats.get("residue_in_mognet_handler", 0),
                "residue_gil_amount_unknown": scanned["junk"].get("gil_amount_unknown", 0),
            },
            "catchup_bits": sorted(catchup),
            "excluded": excluded,
            "split_bit_sites": split_bit_clusters(grants),
            "split_bit_sites_dead_arm_twins": split_bit_clusters(
                grants + scanned["arm_rows"], require_dead=True),
            "dead_only_bits": scanned["dead_only_bits"],
            "top20_fields_by_latch_events": [
                {"field": f, "name": names.get(f, "?"), "latch_events": n,
                 "live_grant_sites": live_sites.get(f, 0)}
                for f, n in sorted(ev_fields.items(), key=lambda kv: (-kv[1], kv[0]))[:20]
            ],
            "events": events,
            "grants": grants,
        }

    gates = run_gates(out)
    out["gates"] = [{"gate": n, "ok": ok, "detail": d} for n, ok, d in gates]

    if "--check" not in argv:
        with open(dest, "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=1)

    print(json.dumps({"summary": out["summary"], "row_classes": out["row_classes"],
                      "junk_payload_rows_dropped": out["junk_payload_rows_dropped"],
                      "top20_fields_by_latch_events": out["top20_fields_by_latch_events"]},
                     indent=2))
    print()
    bad = 0
    for name, ok, detail in gates:
        print("  [%s] %-38s %s" % ("PASS" if ok else "FAIL", name, detail))
        bad += 0 if ok else 1
    if "--check" not in argv:
        print(f"\nwrote {dest}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
