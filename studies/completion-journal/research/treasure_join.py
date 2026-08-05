"""treasure_join.py -- v2.1, the REWARD-EVENT atlas generator (section 7.2 Q2).

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
4. THE SAME-FUNCTION WRITE FALLBACK v1's docstring promised but never implemented. v2
   shipped it as an EVENT-forming class; v2.1 demotes it to a row diagnostic (see below).
5. PATH-GATED WRITE SIDE (fixes F4, a proven LIVE false pairing). v1 took every bit
   write inside ``innermost_guard_block``'s region, so an UNGUARDED grant sitting at a
   macro's join label inherited the PREVIOUS chest's bit (field 600 joined
   ``AddItem(key item #32)`` to 7658/7659, two different neighbours, for one item). v2
   accepts a write only when its block DOMINATES the grant's block (or is the same block)
   -- the real ``if (bit==0) { bit=1; AddItem }`` shape always dominates. v2.1 widens the
   rule to "on the grant's OWN PATH" in both directions and applies it to the weak classes
   too (see v2.1 fix 2).
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
8. F5 SPLIT-BIT REPORTING. When rows of one reward macro disagree about the bit, the atlas
   records the disagreement on both events instead of silently picking one -- twice: over
   live rows ("does a live reward still split?") and over a live row against its dead twin
   ("is that how the bad bit got in?"). v2.1 fixed BOTH halves of this detector; see fix 4.
9. THE DIGEST RANKS BY DISTINCT LATCH EVENTS, not by grant-site verbosity. v1's top-20 put
   the same Treno room in slots 1 and 2 (911 and 1911 are one room) and gave slot 17 to a
   field with 18 "grants" and zero rewards.

v2.1 -- THE FIX SET AN ADVERSARIAL VERIFY PASS PROVED NECESSARY. Every item below is a
defect it demonstrated at the byte level against v2's own output, not a refinement:

1. THE WEAK CLASSES NO LONGER FORM EVENTS BY THEMSELVES. ``latch-fallback`` and
   ``latch-guard`` are PAIRINGS WITH NO PATH EVIDENCE by construction -- v2 admitted every
   row it classed that way (20 of them, one already caught as a catch-up bit) with no bar at
   all to clear, and two of the resulting events were provably wrong: bit 810 (field 2950's
   GysahlGreens, guard-side only) has ZERO writers in all 818 field scripts, so that event
   could never flip to collected; bit 3612 (fields 2111/2114) is SET by 8 fields and
   CLEARED by 3, a reused housekeeping transient, and its "event" merged two different
   Lindblum rooms with two different key items. They stay as ROW classes; to reach the
   atlas a row of theirs must now pass a CORPUS-WIDE WRITER CENSUS (``_promotion_verdict``):
   the bit must be written by at least one field, by NO field outside the reward's own grant
   sites, by exactly ONE room (disc variants ``f`` and ``f+1000`` are one room -- Treno's
   908/1908 key item #50 is the case that forbids a literal "exactly one field id"), and by
   NOBODY anywhere that also clears it. MEASURED on this corpus: 23 weak rows, of which 11
   promote (9 distinct bits, including the four the verify pass hand-confirmed -- 2981, 2662,
   7439, 7568), 11 are refused and listed with their full evidence in ``promotion_refused``,
   and 1 (field 657's GastroFork on 3247) was already excluded as a catch-up bit. Net effect
   on the atlas: 418 events -> 410. All 8 lost events sat OUTSIDE every Treasure-Hunter band
   and were flagged ``story_gate_suspect`` -- 810, 1417, 2055, 2067, 2069, 2088, 3612, 3815.
2. A CLAIM MUST SIT ON THE GRANT'S OWN PATH. Dominance alone left one hole: the guard-side
   promotion accepted ANY write in the function (``field 2952``: ``Bit[1157]=1`` in blk 4,
   key item #69 granted in blk 6 whose dominators are {0,6} -- blk 6 is also reached from
   blk 5, the inventory-full arm, so the key item is granted on a path that never writes
   1157 and a journal keyed on it reports the item uncollected for a player who has it).
   v2.1 computes POST-DOMINATORS over the same folded live subgraph as the reachability
   pass and requires the write block to DOMINATE or POST-DOMINATE the grant block: either
   "the write always already happened" or "the write always still happens". Both mean
   reaching the grant implies the write. A sibling arm is neither. Because a fallback claim
   also requires the function to write exactly one bit, "on the path" and "nearest on the
   path" coincide there. This keeps field 2800's key item #67 (write 138 bytes later at the
   cutscene tail, but on every exit path) and kills field 2952's key item #69.
3. THE CLEAR SIDE IS CENSUSED. v2 recorded only ``Bit[N] = 1`` / computed-pure writes, so a
   ``Bit[N] = 0`` was invisible -- including in ``Main_Init``, where a CLEAR is stronger
   evidence of a transient than a set. 94 bits are cleared by live code corpus-wide, 29 of
   them by some field's own ``Main_Init``. Events now carry ``cleared_by`` (which fields
   zero the bit) and ``main_init_cleared``; field 706's own entry-8 handler zeroes
   7681/7682/7683, so the PhoenixPinion/Tent/Ether events say so on their face.
4. THE SPLIT DETECTOR NOW MEASURES THE REAL GEOMETRY. v2's docstring claimed both F5
   reports "come back empty ... upgrades 1 and 5 close the class outright". That was an
   over-claim twice over: F5's founding case is still in the bytes (field 2803 e23 tag3 --
   the dead clamped-gil arm at 9544 names 2969, the Hammer-trade quest gate, while the live
   ``AddItem(Excalibur)`` at 9646 names 7360), and it was invisible for TWO reasons, a
   32-byte cluster window against a 102-byte macro arm span, and an early ``continue`` that
   dropped dead ``AddGil`` rows before they could be recorded at all. Both are fixed:
   ``_SPLIT_CLUSTER_BYTES`` is 128 (past the measured 102), dead gil arms are recorded, and
   the planted-split gate is planted AT 102 bytes so it calibrates the real geometry instead
   of a spacing that fits comfortably inside the window. The LIVE-vs-LIVE question keeps a
   32-byte window (``_SPLIT_LIVE_CLUSTER_BYTES``) because two DIFFERENT chests of one
   handler sit 106 bytes apart at field 1603 -- the wide window would call that a split, and
   the run reports exactly what it would cost in ``split_bit_sites_live_wide_window``.
   MEASURED, and it is not zero: 66 dead-arm twin clusters, 62 of them a single macro (one
   live row). The other 4 are two macros packed closer than one macro's own 102-byte span,
   which no byte-distance window can separate -- the detector is a SCREEN for a human, not a
   verdict, and every cluster ships its offsets, live flags and rewards so it can be read.
   ``bits_reachable_only_via_dead_code`` also moved 0 -> 18 for the same reason: v2's zero
   was the early ``continue``, not a fact. WHAT IS TRUE ABOUT THE HARM, and all that v2
   should ever have claimed: dead rows are never appended to ``grants``, so none of those 18
   bits (2969 and the 2933/2934/2935 quest-gate trio among them) is an event, and no event
   in the atlas rests on a dead arm. The class is closed AT THE OUTPUT; the disagreement in
   the bytes exists, and is now reported instead of denied.
5. THE 3818 GATE ASSERTS POSITIVE EVIDENCE. "no event for 3818" passes for any reason,
   including a join that lost it. The gate now also requires 3818 to be IN the derived
   catch-up set and that set to intersect NO Treasure-Hunter band, i.e. the filter is
   provably paid for by nothing scored.

Honest limits v2.1 does NOT fix, carried forward so nobody re-derives them: the residue's
``bare`` class still contains the Chocobo Hot & Cold prize shops, Dr. Tot's card top-up and
the ``B_HAVE_ITEM(id)==0``-guarded key items -- all latch-less BY DESIGN, and correctly
excluded from a chest atlas because the INVENTORY is their latch. Treno's key-item sales
are priced at runtime, so their gil events carry ``amount: null`` (never read that as
zero). An event outside every Treasure-Hunter band is flagged ``story_gate_suspect``, not
resolved: this generator can prove a pairing, never a MEANING. And every gate here is
OFFLINE -- per the project brief a green gate suite is a regression harness, not an oracle;
no event in this atlas has yet been checked against a real save or in-game.

Per-grant classes (a row-level diagnostic; the ATLAS unit is the event). The first group
forms events on its own evidence; the second forms one only through the census of fix 1:
  latch        one bit on BOTH sides (guard tests it, an on-path write sets it)
  latch-write  one dominating write-side bit, no guard-side
  indirect     joined at the CALL SITE of the shared reward dispatcher
  --
  latch-guard  one guard-side bit with no on-path write in the function -- weak
  latch-fallback  no region evidence, but the whole function writes exactly one bit
  --
  ambiguous    > 1 candidate on the deciding side
  sc-window    no latch, but a ScenarioCounter guard -- cutscene reward, windowed
  bare         no latch, no SC -- repeatable (shop / dig / top-up grants)
  unresolved   computed item operand outside the dispatcher protocol
  dispatcher   inside the shared reward subroutine -- mechanism, mined at the caller

Every weak-class row carries ``path`` (``dominates`` / ``post-dominates`` / ``off-path`` /
``no-write-in-function``) and, when it did not promote, ``promote_refused`` naming the
census fact that stopped it. Nothing is deleted silently.

Output: ``treasure_join.json`` next to this file (gitignored -- derived from the user's own
install, regenerable), holding the events, the LIVE grant rows only (dead template arms are
never written: a consumer that trusts their amounts inflates gil catastrophically), and the
per-field digest RANKED BY DISTINCT LATCH EVENTS.

Self-check gates run on every invocation (``--check`` runs them against an existing JSON
without rescanning). 14 of them; each is a hand-verified fact from the measurement or the
verify pass, and a failure means the join regressed, not that the gate is stale. Six are
v2.1's, and they are written to fail from BOTH ends -- the quarantine gate demands that 810
and 3612 be gone AND that 2981/2662/7439/7568 survive, because a quarantine that deletes
everything would otherwise pass. Every gate was broken on purpose once (11 mutations that
re-inject the v2 defects into a copy of the JSON, each caught by its own gate).

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
# ONE reward macro's full arm span. MEASURED, not guessed: field 2803 e23 tag3 puts the dead
# clamped-gil arm at 9544 and the live item arm at 9646 -- 102 bytes -- and field 2803 e0
# tag12 spans 124 (1580 -> 1704). v2's 32 could not see either, so its "F5 is empty" was an
# artefact of the window. 128 clears the measured span with room to spare.
_SPLIT_CLUSTER_BYTES = 128
_MACRO_ARM_SPACING = 102                      # the measured f2803 dead-arm -> live-arm distance
# ...but the LIVE-vs-LIVE question needs the tight window: two DIFFERENT chests of one
# handler sit 106 bytes apart (field 1603's Exploda and Elixir, two legitimately different
# bits), so the macro width would report them as a split. The cost of that choice is
# measured every run, in `split_bit_sites_live_wide_window`.
_SPLIT_LIVE_CLUSTER_BYTES = 32
_CALL_LOOKAHEAD = 6                           # instrs after Int16[224]= that may hold the call

# classes whose rows define a reward EVENT on their own path evidence
EVENT_CLASSES = ("latch", "latch-write", "indirect")
# classes with NO path evidence by construction -- row diagnostics that reach the atlas only
# by passing the corpus-wide writer/clearer census (`_promotion_verdict`). v2 admitted these
# unconditionally and shipped two provably-wrong events (bits 810 and 3612).
PROMOTABLE_CLASSES = ("latch-fallback", "latch-guard")


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


def folded_succs(fl, raw: bytes, b: int) -> list:
    """Successors of block *b* with a constant-only branch resolved to the ONE arm taken.

    ``FuncFlow`` treats both successors of a ``JMP_IF(NOT)`` as reachable; when the deciding
    expression is a bare literal the engine takes exactly one of them (engine-exact:
    ``EBin.cs`` beq/bne test the preceding expression's value). Both the reachability pass
    and the post-dominator pass go through this one function ON PURPOSE -- if they disagreed
    about an edge, "post-dominates" would be measured over a graph the fold does not believe.
    """
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
    return [s for s in succs if s is not None]


def folded_reach(fl, raw: bytes) -> set:
    """Block indices reachable from the function entry with const-only branches FOLDED.

    Reused verbatim from the audit's ``constfold.folded_reach``.
    """
    seen = {fl.entry}
    stack = [fl.entry]
    while stack:
        b = stack.pop()
        for s in folded_succs(fl, raw, b):
            if s not in seen:
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

    __slots__ = ("key", "tag", "fl", "raw", "live", "bit_writes", "bit_clears", "gil_consts",
                 "reads_226", "commits_226", "reads_224", "marks_226", "has_computed_grant",
                 "_pdom", "_reach_exit")

    def __init__(self, key, tag, fl, raw):
        self.key = key
        self.tag = tag
        self.fl = fl
        self.raw = raw
        self.live = folded_reach(fl, raw)
        self._pdom = None           # lazy post-dominator bitmasks over the folded live graph
        self._reach_exit = None     # blocks that can reach a live exit (post-dom is UNDEFINED elsewhere)
        self.bit_writes = []        # [(off, block, bit)] -- Bit[N]=1 or Bit[N]=<var>, fold-live
        self.bit_clears = []        # [(off, block, bit)] -- Bit[N]=0, fold-live (v2.1 fix 3)
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
                    # compound ops are not latches. v2.1 fix 3: `Bit[N] = 0` is a CLEAR and is
                    # RECORDED -- v2 dropped it on the floor, which is why a Main_Init clear
                    # (bit 3612 at field 2170, bit 3815 at field 64) was invisible to the atlas.
                    if st.value == 1 or (st.value is None and st.pure):
                        self.bit_writes.append((ins.off, b, st.index))
                        if st.value is None and any(s == 0 and v in (4, 5)
                                                    and i == REWARD_LATCH for s, v, i in refs):
                            self.commits_226.append((ins.off, b, st.index))
                    elif st.value == 0:
                        self.bit_clears.append((ins.off, b, st.index))
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

    def post_dom(self) -> dict:
        """``block -> bitmask of its POST-DOMINATORS`` over the FOLDED LIVE subgraph.

        W post-dominates B when every path from B to a function exit runs through W, so
        "the grant executed" implies "the write executes". Computed on exactly the graph
        :func:`folded_succs` defines, with the same exits the engine would reach.

        Conservative by construction, in the direction that REFUSES claims: a block that
        cannot reach any exit at all gets mask 0 -- no claim. **That mask-0 answer is
        INDETERMINATE, not "off-path"** (v2.2, the re-verify's one proven defect): 4,922 of
        34,867 live functions (14.1%) are unbroken ``while(1)`` handler loops with NO live
        exit block, and inside them a write can sit on the grant's ONLY path while this
        mask still refuses the claim. :meth:`write_path` therefore labels the no-exit case
        ``indeterminate-no-exit`` and never calls it a sibling arm.

        CALIBRATED, not assumed, and scoped honestly: checked block-by-block against the
        brute-force definition ("delete W from the folded live graph; can B still reach an
        exit?") over 4399 real functions and 24198 blocks -- a definition that only exists
        where an exit exists. Within that scope: 4 disagreements, all of them this
        generator claiming LESS at a diverging-loop block; ZERO extra claims. Outside it
        (the 14.1% no-exit class) the mask is a refusal by policy, not a measurement.
        """
        if self._pdom is None:
            fl, raw = self.fl, self.raw
            succ = {b: [s for s in folded_succs(fl, raw, b) if s in self.live]
                    for b in self.live}
            exits = [b for b in self.live if not succ[b]]
            rpred = defaultdict(list)
            for b, ss in succ.items():
                for s in ss:
                    rpred[s].append(b)
            reach_exit, stack = set(exits), list(exits)
            while stack:
                b = stack.pop()
                for p in rpred[b]:
                    if p not in reach_exit:
                        reach_exit.add(p)
                        stack.append(p)
            allm = 0
            for b in reach_exit:
                allm |= 1 << b
            pdom = {b: (1 << b) if not succ[b] else allm for b in reach_exit}
            changed = True
            while changed:
                changed = False
                for b in reach_exit:
                    if not succ[b]:
                        continue
                    m = allm
                    for s in succ[b]:
                        m &= pdom.get(s, 0)     # a successor outside reach_exit contributes 0
                    m |= 1 << b
                    if m != pdom[b]:
                        pdom[b] = m
                        changed = True
            self._pdom = pdom
            self._reach_exit = reach_exit
        return self._pdom

    def can_reach_exit(self, b: int) -> bool:
        """Whether block *b* reaches any live exit -- the domain where post-dominance is
        DEFINED. Outside it, ``post_dom()`` masks are refusals by policy (see its doc)."""
        self.post_dom()
        return b in self._reach_exit

    def path_writes(self, b: int) -> set:
        """Bits whose fold-live write is ON BLOCK *b*'s OWN PATH (v2.1 fix 2).

        On the path = the write's block DOMINATES *b* (it always already happened) or
        POST-DOMINATES it (it always still happens). A write on a SIBLING arm is neither,
        and field 2952's ``Bit[1157]=1`` in blk 4 against the key-item grant in blk 6
        (dominators {0,6}, also reached from the inventory-full arm blk 5) is exactly that.
        """
        mask = self.fl._dom[b] | self.post_dom().get(b, 0)
        return {bit for _off, wb, bit in self.bit_writes if (mask >> wb) & 1}

    def write_path(self, b: int, bit) -> str:
        """How this function's write of *bit* relates to a grant in block *b*.

        ``dominates`` / ``post-dominates`` -> the pairing is path-proven.
        ``off-path``  -> the write exists but on a sibling arm: positive evidence AGAINST.
        ``indeterminate-no-exit`` -> the grant's block reaches no live exit (an unbroken
        ``while(1)`` handler -- 14.1% of live functions), so post-dominance is UNDEFINED:
        neither proof nor a sibling-arm claim. The v2.2 fix: v2.1 stamped this class
        ``off-path`` and shipped a literally false "SIBLING arm" reason on 3 rows (f353).
        ``no-write-in-function`` -> nothing to measure (an inter-procedural guard bit).
        """
        if not isinstance(bit, int):
            return "no-bit"
        wb = [w for _off, w, x in self.bit_writes if x == bit]
        if not wb:
            return "no-write-in-function"
        dm = self.fl._dom[b]
        if any((dm >> w) & 1 for w in wb):
            return "dominates"
        pm = self.post_dom().get(b, 0)
        if any((pm >> w) & 1 for w in wb):
            return "post-dominates"
        if not self.can_reach_exit(b):
            return "indeterminate-no-exit"
        return "off-path"

    def func_writes(self) -> set:
        return {bit for _off, _wb, bit in self.bit_writes}

    def func_clears(self) -> set:
        return {bit for _off, _wb, bit in self.bit_clears}

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
        # v2 promoted a guard-side-only bit to `latch` when ANYBODY in the function set it.
        # v2.1 fix 2: the write must be on the GRANT'S OWN PATH. Measured cost of the change
        # -- 5 rows took this branch corpus-wide; 2 (bit 7553 at fields 1607/1706) are
        # post-dominated and stay `latch`, 3 (field 353's bits 2067/2069) are off-path and
        # drop to `latch-guard`, where the census then refuses them: both bits are written by
        # more fields than grant the reward.
        return ("latch", gb) if gb in fs.path_writes(b) else ("latch-guard", gb)
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
    """``(catchup, main_init_written, main_init_cleared)`` -- upgrade 6 and its two siblings.

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

    ``main_init_cleared`` = every bit any Main_Init ZEROES (v2.1 fix 3). v2 could not see
    this class at all -- the scan only recorded ``value == 1`` and computed-pure writes -- and
    a Main_Init CLEAR is STRONGER evidence of a per-visit transient than a Main_Init set: the
    field resets it every time the player walks in. 29 bits corpus-wide, including 3612
    (field 2170's entry-0 tag-0) and 3815 (field 64's own Main_Init), the two the verify pass
    named. Flagged on the event, and evidence in the promotion census.
    """
    out = set()
    init_written = set()
    init_cleared = set()
    for (ei, fi), fs in scans.items():
        if ei != 0 or fs.tag not in (0, 10):
            continue
        init_written |= fs.func_writes()
        init_cleared |= fs.func_clears()
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
    return out, init_written, init_cleared


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
    main_init_cleared: set = set()
    dead_bits: dict = defaultdict(set)      # bit -> {fields} seen ONLY in dead arms
    live_bits: set = set()
    arm_rows: list = []                     # dead template arms that still name a bit (F5)
    # v2.1 fix 1+3 -- the CORPUS-WIDE censuses. Every fold-live `Bit[N]=1` / `Bit[N]=0` in
    # every function of every field, whether or not it is anywhere near a grant. These are
    # what a weak-class pairing has to survive: a bit nobody writes can never flip to
    # collected (810), and a bit eight rooms write and three rooms clear is a shared
    # transient, not a treasure latch (3612).
    bit_written_by: dict = defaultdict(set)
    bit_cleared_by: dict = defaultdict(set)

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
        _cu, _mi, _mc = catchup_bits(eb, scans)
        catchup |= _cu
        main_init_bits |= _mi
        main_init_cleared |= _mc
        for fs in scans.values():
            for _off, _wb, bit in fs.bit_writes:
                bit_written_by[bit].add(fid)
            for _off, _wb, bit in fs.bit_clears:
                bit_cleared_by[bit].add(fid)

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
                            # v2.1 fix 4, the OTHER half of F5's blindness: v2 `continue`d
                            # here, so a dead CLAMPED-GIL arm never reached the arm-row
                            # recorder below -- and that arm is precisely F5's founding case
                            # (field 2803 off 9544 names bit 2969). Fall through instead.
                            dead_rows["gil"] += 1
                            row = {"kind": "gil", "id": None, "amount": amt}
                        else:
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
                                             "kind": row.get("kind"),
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
                        if cls in PROMOTABLE_CLASSES:
                            # v2.1 fix 2: the weak classes carry their path evidence ON THE
                            # ROW, so a refusal downstream can cite it instead of asserting it.
                            row["path"] = fs.write_path(b, latch)
                    elif fs.is_mognet_handler:
                        row["mognet_handler"] = True
                        stats["residue_in_mognet_handler"] += 1
                    grants.append(row)

    return {"grants": grants, "stats": stats, "junk": junk, "dead_rows": dead_rows,
            "catchup": catchup, "arm_rows": arm_rows,
            "main_init_bits": main_init_bits, "main_init_cleared": main_init_cleared,
            "bit_written_by": bit_written_by, "bit_cleared_by": bit_cleared_by,
            "dead_only_bits": sorted(b for b in dead_bits if b not in live_bits)}


# ---------------------------------------------------------------------------
# events (the atlas unit)


def split_bit_clusters(rows, width=_SPLIT_CLUSTER_BYTES, require_dead=False):
    """F5: rows of ONE reward macro that disagree about the latch bit.

    Reported, never silently resolved -- v1's classifier picked whichever bit the
    surrounding block happened to contain (field 2803 put the item rows on 7360 and the gil
    row on 2969, the Hammer-trade quest gate).

    Two calls, two questions, and v2.1 gives them DIFFERENT windows because they have
    different geometry. ``require_dead=False`` asks "do two LIVE rows of one macro
    disagree?" and runs at ``_SPLIT_LIVE_CLUSTER_BYTES`` (two live rows of one macro are the
    22-byte message twins; 106 bytes apart is two different chests).
    ``require_dead=True`` asks the sharper one -- "does a DEAD template arm name a different
    bit than its live twin?" -- and runs at ``_SPLIT_CLUSTER_BYTES``, which must clear the
    MEASURED 102-byte arm span or the detector reports zero for want of a window, which is
    exactly what v2 did.

    The cluster is ANCHORED, not chained: a row joins when it is within *width* of the
    cluster's FIRST row, not of its last. Chaining let four adjacent chests 126 bytes apart
    fuse into one 624-byte "macro" (field 764), which is not what a macro is. Every emitted
    cluster therefore has ``span <= width`` by construction.
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
            if r["off"] - cluster[0]["off"] <= width:
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
             "span": max(r["off"] for r in cluster) - min(r["off"] for r in cluster),
             "live": [bool(r.get("live", True)) for r in cluster],
             "rewards": [_reward_label(r) for r in cluster]}]


def _reward_label(r) -> str:
    if r.get("label"):
        return r["label"]
    if r.get("amount") is not None:
        return "%s gil" % r["amount"]
    return "%s (computed)" % (r.get("kind") or "?")


def _promotion_verdict(bit, row, grant_fields, written, cleared):
    """May a weak-class row (``latch-fallback`` / ``latch-guard``) define an EVENT?

    v2.1 fix 1. ``None`` = promote; otherwise EVERY census fact that refuses it (joined with
    ``; ``), verbatim into ``promotion_refused`` so the refusal is auditable and nothing
    vanishes silently. All clauses are evaluated, not short-circuited: bit 3612 fails three
    of them at once and a reader should see all three.

    Every clause was written against a row the verify pass PROVED wrong or PROVED right:

    * ``no-writer-corpus-wide`` -- bit 810 (field 2950's GysahlGreens). Zero fold-live writes
      anywhere in 818 scripts: an atlas row that can never flip to collected.
    * ``off-path-write`` -- field 2952's key item #69 (fix 2). Positive evidence AGAINST, not
      absence of evidence: the function DOES write the bit, on a sibling arm.
    * ``written-outside-this-reward`` / ``written-by-N-rooms`` -- bit 3612 (fields
      2111/2114): eight rooms set it, and it is on PLAN.md's own "reused compiled
      dispatch/housekeeping" exclusion list. Disc variants (``f`` and ``f+1000``) are ONE
      room -- a literal "exactly one field id" would drop Treno's 908/1908 key item #50,
      which the atlas merges by design and the verify pass did not fault.
    * ``cleared-by`` -- bit 3815, whose single writer (field 64) also zeroes it in its own
      Main_Init. A bit its own room resets is a per-visit transient, not a collection latch.
    """
    writers = set(written.get(bit, ()))
    clearers = sorted(cleared.get(bit, ()))
    why = []
    if not writers:
        why.append("no-writer-corpus-wide")
    if row.get("path") == "off-path":
        why.append("off-path-write (the function writes the bit on a SIBLING arm)")
    elif row.get("path") == "indeterminate-no-exit":
        # v2.2: TRUTHFUL, and distinct from off-path -- the function never exits, so
        # post-dominance is undefined; the write may well be on the only path. Still
        # refuses promotion (no proof), but never claims a sibling arm that isn't there.
        why.append("path-indeterminate (the function never exits; post-dominance undefined)")
    why.extend(_shared_writer_clauses(writers, grant_fields))
    if clearers:
        why.append("cleared-by %s" % (clearers[:6],))
    return "; ".join(why) or None


def _shared_writer_clauses(writers, grant_fields):
    """The shared-writer refusal clauses, shared by the weak-row promotion AND the
    all-class join rule (v2.2): a bit written outside the reward's own fields means the
    bit's meaning is not this reward, whatever the row's class. Disc variants
    (``f % 1000``) are one room, exactly as the promotion census counts them."""
    why = []
    outside = sorted(writers - set(grant_fields))
    if outside:
        why.append("written-outside-this-reward by %s" % (outside[:6],))
    rooms = {f % 1000 for f in writers}
    if len(rooms) > 1:
        why.append("written-by-%d-rooms %s" % (len(rooms), sorted(writers)[:6]))
    return why


def build_events(grants, names, catchup, main_init_bits, main_init_cleared,
                 bit_written_by, bit_cleared_by):
    """Group LIVE, latched grants into reward EVENTS keyed on the latch bit (upgrade 5).

    v2.1: only :data:`EVENT_CLASSES` enter on their own evidence. A
    :data:`PROMOTABLE_CLASSES` row must first pass :func:`_promotion_verdict`.
    """
    splits = {}
    for s in split_bit_clusters(grants, width=_SPLIT_LIVE_CLUSTER_BYTES):
        for bit in s["bits"]:
            splits.setdefault(bit, []).append(s)

    # the reward's OWN sites: every field holding a live grant row that names this bit. A
    # writer outside this set is a field that touches the bit for some other reason.
    grant_fields: dict = defaultdict(set)
    for g in grants:
        if isinstance(g.get("latch"), int):
            grant_fields[g["latch"]].add(g["field"])

    events: dict = {}
    refused: list = []
    excluded = {"catchup": defaultdict(set), "mognet": defaultdict(set)}
    census: dict = {}
    for g in grants:
        bit = g.get("latch")
        if not isinstance(bit, int):
            continue
        promotable = g["cls"] in PROMOTABLE_CLASSES
        why = None
        if promotable:
            why = _promotion_verdict(bit, g, grant_fields[bit], bit_written_by, bit_cleared_by)
            census.setdefault(bit, {
                "writers": sorted(bit_written_by.get(bit, ())),
                "clearers": sorted(bit_cleared_by.get(bit, ())),
                "grant_fields": sorted(grant_fields[bit]),
                "main_init_cleared": bit in main_init_cleared,
                "catchup": bit in catchup,
                "rows": [],
            })["rows"].append({"field": g["field"], "off": g["off"], "cls": g["cls"],
                               "path": g.get("path"), "reward": _reward_label(g),
                               "promoted": why is None and bit not in catchup
                               and bit not in MOGNET_BAND,
                               "refused": why})
        elif g["cls"] not in EVENT_CLASSES:
            continue
        # the corpus-level disqualifications outrank the evidence bar, and are counted the
        # way v2 counted them: a catch-up bit is excluded as a catch-up bit even when its row
        # would also have failed the census (field 657's GastroFork is both).
        if bit in catchup:
            excluded["catchup"][bit].add(g["field"])
            continue
        if bit in MOGNET_BAND:
            excluded["mognet"][bit].add(g["field"])
            continue
        # v2.2: the shared-writer rule is a JOIN rule for EVERY class, not only a census
        # clause on weak rows. The re-verify proved the prior shape by construction: with
        # post-dominance repaired, f353's rows re-enter as class `latch`, `latch` never
        # consulted the census, and only the no-shared-bit GATE stopped events 2067/2069
        # -- a gate doing a join's job by accident. The rule mirrors the gate EXACTLY
        # (writers OUTSIDE the reward's own grant fields): the weak-row census's extra
        # `written-by-N-rooms` heuristic must NOT apply here -- it refuses legitimate
        # multi-room chests (the Cleyra Sandpit/Inn shared-bit class), measured as a
        # 410 -> 333 collapse when it briefly did.
        if why is None and not promotable:
            outside = sorted(set(bit_written_by.get(bit, ())) - grant_fields[bit])
            if outside:
                why = "written-outside-this-reward by %s" % (outside[:6],)
        if why is not None:
            g["promote_refused"] = why
            refused.append({"field": g["field"], "entry": g["entry"], "func": g["func"],
                            "off": g["off"], "bit": bit, "cls": g["cls"],
                            "path": g.get("path"), "reward": _reward_label(g),
                            "reason": why,
                            "writers": sorted(bit_written_by.get(bit, ())),
                            "clearers": sorted(bit_cleared_by.get(bit, ()))})
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
        if bit in main_init_cleared:
            # v2.1 fix 3: STRONGER than the above. Some field's Main_Init ZEROES this bit, so
            # it is reset on entry -- a per-visit transient wearing a latch's clothes.
            row["main_init_cleared"] = True
        cl = sorted(bit_cleared_by.get(bit, ()))
        if cl:
            # v2.1 fix 3: which fields execute a fold-live `Bit[N] = 0`. Field 706 zeroes
            # 7681/7682/7683 in its own entry-8 handler, so its PhoenixPinion/Tent/Ether
            # events say so on their face instead of looking like clean 1-pt chests.
            row["cleared_by"] = cl
        wr = sorted(bit_written_by.get(bit, ()))
        if wr != fields:
            # the bit is written by fields other than the ones granting the reward (or, for a
            # purely inter-procedural guard bit, by none of them). Not fatal -- `latch` rows
            # carry their own path proof -- but it is the shared-bit axis a catalog must see.
            row["writer_fields"] = wr
        if set(ev["classes"]) & set(PROMOTABLE_CLASSES):
            row["promoted_by_census"] = True     # no path proof; the census carried it
        if bit in splits:
            row["split_bit"] = sorted({b for s in splits[bit] for b in s["bits"]})
        out.append(row)
    return (out,
            {k: {str(b): sorted(f) for b, f in v.items()} for k, v in excluded.items()},
            refused,
            {str(b): census[b] for b in sorted(census)})


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

    # v2.1 fix 5. "no event for 3818" passes for ANY reason, including a join that lost the
    # bit entirely, so the gate now demands the positive facts too: 3818 must be IN the
    # derived catch-up set, and that set must cost the atlas nothing scored.
    cu = set(out["catchup_bits"])
    cu_in_bands = sorted(cu & (_TH_SINGLE | _TH_DOUBLE | _TH_UNSCORED_GAP))
    res.append(("bit-3818-catchup-derived-and-bands-clean",
                3818 in cu and not any(e["bit"] == 3818 for e in events)
                and not cu_in_bands,
                "3818 in derived set=%s; no event=%s; catchup(%d) INTERSECT TH bands=%s"
                % (3818 in cu, not any(e["bit"] == 3818 for e in events), len(cu),
                   cu_in_bands or "empty")))

    b911 = {e["bit"] for e in _field_events(events, 911)}
    b1911 = {e["bit"] for e in _field_events(events, 1911)}
    merged = all(sorted(e["fields"]) == [911, 1911]
                 for e in events if e["bit"] in (b911 | b1911))
    res.append(("treno-911-1911-one-event-set",
                bool(b911) and b911 == b1911 and merged,
                "911=%s 1911=%s merged=%s" % (sorted(b911), sorted(b1911), merged)))

    # v2.1 fix 4. v2 planted its twin 22 bytes apart -- a spacing that fits comfortably
    # inside its own 32-byte window, so the probe could pass while the detector was blind to
    # the geometry that actually occurs. Plant at the MEASURED 102 (field 2803's dead arm at
    # 9544 vs its live arm at 9646) and require BOTH directions: the macro window sees it,
    # the live window does not (which is why the live question keeps its own narrow width).
    planted = [
        {"field": 0, "entry": 0, "func": 0, "off": 1000, "latch": 11, "live": True},
        {"field": 0, "entry": 0, "func": 0, "off": 1000 + _MACRO_ARM_SPACING,
         "latch": 22, "live": False},
    ]
    probe = split_bit_clusters(planted, require_dead=True)
    probe_narrow = split_bit_clusters(planted, width=_SPLIT_LIVE_CLUSTER_BYTES,
                                      require_dead=True)
    res.append(("split-detector-calibrated-at-the-102-byte-macro-spacing",
                len(probe) == 1 and len(probe_narrow) == 0,
                "planted at %dB -> macro window(%d)=%d cluster(s), live window(%d)=%d; "
                "corpus reports %d live / %d dead-twin"
                % (_MACRO_ARM_SPACING, _SPLIT_CLUSTER_BYTES, len(probe),
                   _SPLIT_LIVE_CLUSTER_BYTES, len(probe_narrow),
                   len(out["split_bit_sites"]), len(out["split_bit_sites_dead_arm_twins"]))))

    # ...and the same detector must find F5's FOUNDING CASE in the real bytes. A planted
    # split proves the code runs; only this proves the window fits the corpus.
    # BOTH cases the verify pass named, by offset: e23 tag3 (the dead clamped-gil arm at
    # 9544 on 2969 vs the live Excalibur at 9646 on 7360) and e0 tag12 (1580 on 2935 vs
    # 1704 on 7566).
    tw = out["split_bit_sites_dead_arm_twins"]
    a = [s for s in tw if s["field"] == 2803 and s["entry"] == 23
         and s["bits"] == [2969, 7360] and 9544 in s["offs"] and 9646 in s["offs"]]
    b = [s for s in tw if s["field"] == 2803 and s["entry"] == 0
         and s["bits"] == [2935, 7566] and 1580 in s["offs"] and 1704 in s["offs"]]
    res.append(("f2803-founding-dead-arm-splits-are-detected", bool(a) and bool(b),
                "e23=%s | e0=%s" % (a[0] if a else None, b[0] if b else None)))

    ev = next((e for e in events if e["bit"] == 7648), None)
    ok = bool(ev) and 600 in ev["fields"] \
        and any(r["kind"] == "gil" and r.get("amount") == 5000 for r in ev["rewards"]) \
        and not any(r["kind"] == "item" and r.get("id", 0) >= 1000 for r in ev["rewards"])
    res.append(("f600-bit-7648-live-arm-is-5000-gil", ok,
                "event=%s" % (ev["rewards"] if ev else None)))

    # -- v2.1 fix 1: the quarantine, proven from BOTH ends ------------------------------
    cen = out["promotion_census"]
    c810, c3612 = cen.get("810", {}), cen.get("3612", {})
    ok = (not any(e["bit"] == 810 for e in events)
          and not any(e["bit"] == 3612 for e in events)
          and c810.get("writers") == []
          and len(c3612.get("writers", [])) >= 2 and len(c3612.get("clearers", [])) >= 1)
    res.append(("zero-writer-and-shared-bits-refused", ok,
                "810 writers=%s event=%s | 3612 writers=%s clearers=%s event=%s"
                % (c810.get("writers"), any(e["bit"] == 810 for e in events),
                   c3612.get("writers"), c3612.get("clearers"),
                   any(e["bit"] == 3612 for e in events))))

    # the OTHER end: the census must still PROMOTE the rows the verify pass hand-confirmed,
    # or "quarantine" would just be a delete. 2981 = f2800 key item #67 (write 138 bytes
    # later but on every exit path), 2662 = f564's inter-procedural guard bit, 7439 = the
    # f358 key item #31 upgrade 4 was built for, 7568 = Treno 908/1908 key item #50.
    kept = {b: next((e for e in events if e["bit"] == b), None)
            for b in (2981, 2662, 7439, 7568)}
    promoted = [e["bit"] for e in events if e.get("promoted_by_census")]
    res.append(("census-promotes-the-hand-confirmed-weak-rows",
                all(kept.values()) and all(e.get("promoted_by_census") for e in kept.values()
                                           if e) and len(promoted) >= 4,
                "kept=%s; events promoted by census=%d %s"
                % ({b: bool(e) for b, e in kept.items()}, len(promoted), promoted)))

    # -- v2.1 fix 2: the sibling arm ---------------------------------------------------
    ev1157 = next((e for e in events if e["bit"] == 1157), None)
    ids = [r.get("id") for r in (ev1157 or {}).get("rewards", [])]
    ref = [r for r in out["promotion_refused"] if r["bit"] == 1157 and r["field"] == 2952]
    res.append(("f2952-sibling-arm-key-item-69-not-latched-on-1157",
                bool(ev1157) and 325 not in ids and 566 in ids
                and bool(ref) and ref[0]["path"] == "off-path",
                "1157 rewards=%s; refused=%s"
                % (ids, [(r["off"], r["reward"], r["reason"]) for r in ref])))

    # -- v2.1 fix 3: the clear side ----------------------------------------------------
    # the three 1-pt Gizamaluke chests whose bits field 706's OWN entry-8 handler zeroes at
    # 12043/12052/12061. The labels are pinned too, so the gate cannot pass on some other
    # three events that happen to be cleared.
    f706_clear = {7683: "PhoenixPinion", 7682: "Tent", 7681: "Ether"}
    got = {b: next((e for e in events if e["bit"] == b), None) for b in f706_clear}
    res.append(("f706-clears-7681-7683-are-flagged-on-their-events",
                all(e is not None and 706 in e.get("cleared_by", [])
                    and e["th_band"] == "1pt"
                    and [r.get("label") for r in e["rewards"]] == [f706_clear[b]]
                    for b, e in got.items()),
                "%s" % {b: (None if e is None else (e.get("cleared_by"),
                                                    [r.get("label") for r in e["rewards"]]))
                        for b, e in got.items()}))

    # v2.2: the shared-writer rule is a JOIN rule for every class (the re-verify proved the
    # gate below was doing a join's job by accident). This synthetic gate BREAKS it once per
    # run, in-process, exactly like the planted split: a strong `latch` row whose bit has an
    # outside writer must be refused with the written-outside reason, and the sole-writer
    # control must produce the event. If someone re-scopes the rule back to weak rows only,
    # THIS fails -- the corpus gate below cannot (today's corpus has zero such events).
    def _mk(bit):
        return {"latch": bit, "cls": "latch", "field": 1, "entry": 0, "func": 3, "off": 100,
                "kind": "item", "id": 5, "label": "Potion", "count": 1}
    _pe, _, _pref, _ = build_events([_mk(500)], {}, set(), set(), set(), {500: {1, 2}}, {})
    _ce, _, _cref, _ = build_events([_mk(500)], {}, set(), set(), set(), {500: {1}}, {})
    res.append(("shared-writer-JOIN-rule-fires-on-a-strong-row (synthetic)",
                not _pe and _pref and "written-outside-this-reward" in _pref[0]["reason"]
                and len(_ce) == 1 and not _cref,
                "poisoned: events=%d refused=%r | control: events=%d refused=%d"
                % (len(_pe), _pref[0]["reason"] if _pref else None, len(_ce), len(_cref))))

    # the shared-bit axis after the quarantine. The verify pass measured 4 of v2's 418 event
    # bits as set by more fields than the event listed; all four were weak-class events and
    # are now refused, so this must be zero -- and it is a GATE, not a note, because the flag
    # would otherwise be surface nothing ever exercises.
    shared = [(e["bit"], e["fields"], e["writer_fields"])
              for e in events if e.get("writer_fields")]
    res.append(("no-event-rests-on-a-bit-another-room-also-sets", not shared,
                "offenders=%s" % (shared[:4] or "none of %d events" % len(events))))

    mic = set(out["main_init_cleared_bits"])
    res.append(("main-init-CLEARS-are-censused (3612, 3815)",
                {3612, 3815} <= mic
                and not any(e["bit"] in (3612, 3815) for e in events),
                "main-init-cleared bits=%d; 3612=%s 3815=%s; neither is an event=%s"
                % (len(mic), 3612 in mic, 3815 in mic,
                   not any(e["bit"] in (3612, 3815) for e in events))))

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
        events, excluded, refused, census = build_events(
            grants, names, catchup, scanned["main_init_bits"],
            scanned["main_init_cleared"], scanned["bit_written_by"],
            scanned["bit_cleared_by"])
        stats = scanned["stats"]
        dead_twins = split_bit_clusters(grants + scanned["arm_rows"], require_dead=True)
        live_splits = split_bit_clusters(grants, width=_SPLIT_LIVE_CLUSTER_BYTES)
        # what the WIDE window would say about the live-vs-live question -- measured, so the
        # two-width choice is a reported cost and not an assertion (field 1603's Exploda and
        # Elixir sit 106 bytes apart on two legitimately different bits).
        live_splits_wide = split_bit_clusters(grants, width=_SPLIT_CLUSTER_BYTES)

        ev_fields = defaultdict(int)
        for e in events:
            for f in e["fields"]:
                ev_fields[f] += 1
        live_sites = Counter(g["field"] for g in grants)

        cls_counts = Counter(g["cls"] for g in grants)
        th_counts = Counter(e["th_band"] for e in events)
        out = {
            "generator": "studies/completion-journal/research/treasure_join.py (v2.1)",
            "unit": "reward EVENT keyed on the latch bit (disc-variant fields merged)",
            "event_evidence": {
                "event_classes": list(EVENT_CLASSES),
                "promotable_classes": list(PROMOTABLE_CLASSES),
                "rule": "EVENT_CLASSES enter on path evidence (the write DOMINATES or "
                        "POST-DOMINATES the grant block on the folded live CFG). A "
                        "PROMOTABLE row enters only if the corpus census says: >=1 writer, "
                        "no writer outside the reward's own grant fields, exactly one room "
                        "(f and f+1000 are one room), no clearer anywhere, and no off-path "
                        "write in its own function.",
            },
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
                "split_bit_dead_arm_twin_disagreements": len(dead_twins),
                # a single-macro cluster holds exactly ONE live row (the macro grants once);
                # the rest are two macros packed closer than one macro's own 102-byte span,
                # which no byte-distance window can separate. The detector is a SCREEN.
                "split_bit_dead_arm_twins_single_macro": sum(1 for s in dead_twins
                                                             if sum(s["live"]) == 1),
                "split_bit_live_splits_at_the_macro_window": len(live_splits_wide),
                "weak_rows_total": sum(len(c["rows"]) for c in census.values()),
                "weak_rows_promoted": sum(1 for c in census.values()
                                          for r in c["rows"] if r["promoted"]),
                "weak_rows_refused_by_census": len(refused),
                "events_promoted_by_census": sum(1 for e in events
                                                 if e.get("promoted_by_census")),
                "events_cleared_somewhere": sum(1 for e in events if e.get("cleared_by")),
                # the shared-bit axis, measured after the quarantine: the verify pass's
                # independent audit found 4 of v2's 418 event bits set by MORE fields than
                # the event listed (2055, 2067, 2069, 3612) -- all four are now refused, and
                # this counts what is left. A zero here is the claim "no event in the atlas
                # rests on a bit some other room also sets".
                "events_with_writers_outside_their_fields": sum(
                    1 for e in events if e.get("writer_fields")),
                "events_main_init_cleared": sum(1 for e in events
                                                if e.get("main_init_cleared")),
                "bits_cleared_corpus_wide": len(scanned["bit_cleared_by"]),
                "bits_main_init_cleared": len(scanned["main_init_cleared"]),
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
            "promotion_census": census,
            "promotion_refused": refused,
            "main_init_cleared_bits": sorted(scanned["main_init_cleared"]),
            "bit_cleared_by": {str(b): sorted(f)
                               for b, f in sorted(scanned["bit_cleared_by"].items())},
            "split_bit_sites": live_splits,
            "split_bit_sites_dead_arm_twins": dead_twins,
            "split_bit_sites_live_wide_window": live_splits_wide,
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
        print("  [%s] %-52s %s" % ("PASS" if ok else "FAIL", name, detail))
        bad += 0 if ok else 1
    if "--check" not in argv:
        print(f"\nwrote {dest}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
