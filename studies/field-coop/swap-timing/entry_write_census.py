#!/usr/bin/env python3
"""Entry-write census: what does each field's Main_Init write to save-persistent story state?

Owner decision 5 of studies/field-coop/SWAP-TIMING-S164.md.  The guest's story pin stages the host's story frame
captured BEFORE the host's landing hook, and the guest copy's own Main_Init then runs on it.  So the question is what
Main_Init (and the Init function it starts first) does to save-persistent variables.

Usage:  py entry_write_census.py [EXPORTS_DIR] [--manifest TSV] [--json OUT.json] [--compare-langs]
Input:  the Hades Workshop field-script exports (test2_N.txt, 817 files).  The `us` section of each export is the one
        classified; --compare-langs also classifies the other language sections and reports any that differ.
Scope:  the Main_Init function, plus the Init (tag 0) function of the entry Main_Init starts FIRST
        (the first InitCode/InitObject/InitRegion call in source order).  Nothing else is followed.
Output: counts per class, the random-gated and bytes 2-3 lists with `file:line` cites, and what the pass could not see.

Variable classes.  HW's names are INVERTED against the engine's (memory project-ff9-eb-script-tooling):
    VAR_Gen*  / VARL_Gen*          engine Global = gEventGlobal = SAVE-PERSISTENT   (the story state)        scanned
    General_* / Setting_* / ...    named gEventGlobal words/bytes (ScenarioCounter = bytes 0-1,
                                   FieldEntrance = bytes 2-3, LoadedGame = byte 184)                         scanned
    VAR_Glob* / VARL_Glob*         engine Map = transient, wiped on every field load                         ignored
    VAR_Loc*                       the running entry's own locals                                            ignored
The numeric suffix is a BYTE offset for the byte/word types and a BIT index for the Bool types.

Each persistent write statement gets ONE class, assigned in this order:
    prologue           the stock block every field opens with (see PROLOGUE_TOKENS): load latch + sound-slot bookkeeping
    bytes 2-3          the target overlaps gEventGlobal bytes 2-3 (General_FieldEntrance)
    random-gated       the value stored comes from GetRandom (directly, or through a variable that took a GetRandom
                       value earlier in the function text), or an enclosing condition tests such a value
    once-gated         an enclosing if/else branch is guarded by a persistent variable that a statement of that same
                       branch (unconditional within it, or the write itself) drives to a state where the guard no
                       longer admits the branch (brute force over the guard variable's small domain)
    read-modify-write  a compound operator, ++/--, an RHS that reads the target, or a guard that reads the target
    set                the RHS is a constant expression and nothing above applies
    derived            the RHS reads other state (a copy or a computed value) and nothing above applies
A field's classes are the set of its write classes, so the per-field counts overlap.
Stdlib only.
"""
import argparse
import collections
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_EXPORTS = r"C:\gd\FFIX\reference\test2"
DEFAULT_MANIFEST = os.path.normpath(os.path.join(HERE, "..", "..", "..", "reference", "field-manifest.tsv"))

CLASSES = ["bytes 2-3", "random-gated", "once-gated", "read-modify-write", "set", "derived"]

# The stock opening block of Main_Init, present in all 817 exports (verified by the census itself).
#   VAR_GenBool_191  = 0                          a handshake bit, always cleared
#   General_LoadedGame = 0 / the 10000 rewrite    the save-load latch; FieldEntrance becomes 10000 only when it was 1
#   VAR_GenInt16_9 / _11 and VAR_GenUInt8_13 / _14   the environment-sound slot 0 / 1 bookkeeping (a slot id and its
#                                                 state; state 9 prints "Error Env Play() Slot=0")
# Each of these is a constant store or a state machine with a fixed point (f(f(x)) == f(x)), so replaying it on either
# frame gives one result.  Counted on their own row so they do not drown the real findings.
PROLOGUE_TOKENS = {"VAR_GenBool_191", "General_LoadedGame", "VAR_GenInt16_9", "VAR_GenInt16_11",
                   "VAR_GenUInt8_13", "VAR_GenUInt8_14"}

# --------------------------------------------------------------------------------------------- variables
VAR_RE = re.compile(r"\b(VARL?_(Gen|Glob|Loc)(Bool|Int8|Int16|Int24|UInt8|UInt16|UInt24)_(\d+))\b"
                    r"|\b((?:General|Setting|Chocobo|Mognet|Minigame|ATE|World)_[A-Za-z0-9]+)\b")
NAMED_BITS = {                                   # named words with a known gEventGlobal position (bit spans)
    "General_ScenarioCounter": (0, 16),          # bytes 0-1
    "General_FieldEntrance": (16, 32),           # bytes 2-3
    "General_LoadedGame": (184 * 8, 185 * 8),    # byte 184
}
FE_SPAN = ("g", 16, 32)
TYPE_BITS = {"Bool": 1, "Int8": 8, "UInt8": 8, "Int16": 16, "UInt16": 16, "Int24": 24, "UInt24": 24}


def var_tokens(text):
    """Yield (token, family, span) for every variable token.  family: Gen | Glob | Loc | named.  span is None for
    Glob/Loc; named words with no known position get a private span, so they only ever overlap themselves."""
    for m in VAR_RE.finditer(text):
        if m.group(1):
            tok, fam, typ, idx = m.group(1), m.group(2), m.group(3), int(m.group(4))
            if typ == "Bool":
                span = ("g", idx, idx + 1)
            else:
                span = ("g", idx * 8, (idx + TYPE_BITS[typ] // 8) * 8)
            yield tok, fam, (span if fam == "Gen" else None)
        else:
            tok = m.group(5)
            if tok in NAMED_BITS:
                yield tok, "named", ("g",) + NAMED_BITS[tok]
            else:
                yield tok, "named", (tok, 0, 1 << 30)


def persistent(fam):
    return fam in ("Gen", "named")


def overlaps(a, b):
    return a is not None and b is not None and a[0] == b[0] and a[1] < b[2] and b[1] < a[2]


# --------------------------------------------------------------------------------------------- export parsing
LANG_RE = re.compile(r"^#HW language (\w+)\s*$")
ENTRY_RE = re.compile(r"^#HW newentry (\d+)")
FUNC_TAG_RE = re.compile(r"^#HW newfunction (\d+)")
FUNC_NAME_RE = re.compile(r"^Function (\S+)")


class Func:
    def __init__(self, entry, tag, name, line):
        self.entry, self.tag, self.name, self.line = entry, tag, name, line
        self.body = []        # (1-based line number, raw text)


def split_sections(lines):
    """-> {lang: {(entry, tag): Func}} in file order.  Lines are cited 1-based, as the file shows them."""
    secs = collections.OrderedDict()
    lang = entry = tag = cur = None
    for n, raw in enumerate(lines, 1):
        m = LANG_RE.match(raw)
        if m:
            lang = m.group(1)
            secs.setdefault(lang, {})
            entry = tag = cur = None
            continue
        if lang is None:
            continue
        m = ENTRY_RE.match(raw)
        if m:
            entry, tag, cur = int(m.group(1)), None, None
            continue
        m = FUNC_TAG_RE.match(raw)
        if m:
            tag, cur = int(m.group(1)), None
            continue
        m = FUNC_NAME_RE.match(raw)
        if m:
            cur = Func(entry, tag, m.group(1), n)
            secs[lang][(entry, tag)] = cur
            continue
        if raw.startswith("#HW"):
            cur = None
            continue
        if cur is not None:
            cur.body.append((n, raw))
    return secs


def strip_comment(s):
    i = s.find("//")
    while i != -1:
        if s[:i].count('"') % 2 == 0:
            return s[:i]
        i = s.find("//", i + 2)
    return s


# --------------------------------------------------------------------------------------------- statement parsing
IF_RE = re.compile(r"^(if|ifnot|while)\s*\(\s*(.*?)\s*\)\s*\{$")
SWITCH_RE = re.compile(r"^switch(ex)?\s+\d+\s*\(\s*(.*?)\s*\)\s*(?:from\s+(-?\d+)\s*)?\{$")
CASE_RE = re.compile(r"^case\s+([+-]?\d+)\s*:$")
EFFECT_RE = re.compile(r"\b(AddItem|AddGil|AddParty|RemoveParty|Party|SetCharacterData|SetHP|SetMP|CureStatus|SetName|"
                       r"AddCharacterAttribute|RemoveCharacterAttribute)\(")
CALL_RE = re.compile(r"^\s*(RunScriptSync|RunScriptAsync|RunScript|RunSharedScript)\(")
SET_RE = re.compile(r"^set\s+([A-Za-z_][A-Za-z0-9_]*)\s*(?:(\+\+|--)|(<<=|>>=|[-+*/%|&^]?=)\s*(.*))$")
INIT_RE = re.compile(r"^(InitCode|InitObject|InitRegion)\(\s*(\d+)\s*,\s*(\d+)\s*\)")
EMBED_RE = re.compile(r"\b((?:VARL?_(?:Gen|Glob|Loc)(?:Bool|Int8|Int16|Int24|UInt8|UInt16|UInt24)_\d+)"
                      r"|(?:General|Setting)_[A-Za-z0-9]+)\s*(\+\+|--|<<=|>>=|[-+*/%|&^]=|(?<![=!<>])=(?!=))\s*(.*)$")


class Frame:
    __slots__ = ("id", "kind", "cond", "pol", "labels", "expr", "base", "nstmt")

    def __init__(self, fid, kind, cond=None, pol=True):
        self.id, self.kind, self.cond, self.pol = fid, kind, cond, pol
        self.labels, self.expr, self.base, self.nstmt = [], None, None, 0


def parse_function(func):
    """-> (writes, inits, problems).  A write: dict(line, target, op, rhs, conds, embedded) where conds is the stack of
    enclosing (frame_id, kind, cond_text, polarity) at that statement, outermost first."""
    writes, inits, problems = [], [], []
    stack = []
    counter = [0]

    def new_frame(kind, cond=None, pol=True):
        counter[0] += 1
        return Frame(counter[0], kind, cond, pol)

    def conds_now():
        return [(f.id, f.kind, f.cond, f.pol) for f in stack]

    for ln, raw in func.body:
        t = strip_comment(raw).strip()
        if not t or t in ("break", "loop") or t.startswith("return"):
            continue
        if stack:
            stack[-1].nstmt += 1
        if t.startswith("}"):
            if stack and stack[-1].kind == "case":       # this brace closes the switch itself
                stack.pop()
            if not stack:
                problems.append((ln, "unbalanced }"))
                continue
            top = stack.pop()
            if t[1:].strip().startswith("else"):
                stack.append(new_frame("else", top.cond, not top.pol))
            continue
        m = IF_RE.match(t)
        if m:
            kw, cond = m.groups()
            writes.extend(embedded_writes(cond, ln, conds_now()))
            stack.append(new_frame("while" if kw == "while" else "if", cond, kw != "ifnot"))
            continue
        if t == "do {":
            stack.append(new_frame("do"))
            continue
        m = SWITCH_RE.match(t)
        if m:
            f = new_frame("switch")
            f.expr = m.group(2)
            f.base = int(m.group(3)) if m.group(3) is not None else None
            stack.append(f)
            continue
        m = CASE_RE.match(t)
        if m or t == "default:":
            if stack and stack[-1].kind == "case" and stack[-1].nstmt <= 1:     # stacked labels share one body
                cf = stack[-1]
                cf.nstmt = 0
            else:
                if stack and stack[-1].kind == "case":
                    stack.pop()
                cf = new_frame("case")
                stack.append(cf)
            sw = next((f for f in reversed(stack) if f.kind == "switch"), None)
            cf.expr = sw.expr if sw else "?"
            if m:
                v = int(m.group(1))
                if m.group(1).startswith("+") and sw is not None and sw.base is not None:
                    v = sw.base + v
                cf.labels.append(str(v))
            else:
                cf.labels.append("default")
            cf.cond = ("default( %s )" % cf.expr if "default" in cf.labels
                       else " || ".join("( %s == %s )" % (cf.expr, v) for v in cf.labels))
            continue
        m = SET_RE.match(t)
        if m:
            target, op1, op2, rhs = m.groups()
            rhs = (rhs or "").strip()
            writes.append(dict(line=ln, target=target, op=op1 or op2, rhs=rhs, conds=conds_now(), embedded=False))
            writes.extend(embedded_writes(rhs, ln, conds_now()))
            continue
        m = INIT_RE.match(t)
        if m:
            inits.append(dict(line=ln, call=m.group(1), entry=int(m.group(2)), tag=int(m.group(3))))
            continue
        if t.endswith("{"):
            problems.append((ln, "unrecognised block opener: " + t[:60]))
            stack.append(new_frame("block"))
    while stack and stack[-1].kind == "case":
        stack.pop()
    if stack:
        problems.append((func.body[-1][0] if func.body else func.line, "unclosed block at end of function"))
    return writes, inits, problems


def embedded_writes(text, ln, conds):
    """Assignments hidden inside an expression, e.g. `set X = ( VARL_GenUInt8_5 += ... )`."""
    return [dict(line=ln, target=m.group(1), op=m.group(2), rhs=m.group(3).strip(), conds=list(conds), embedded=True)
            for m in EMBED_RE.finditer(text)]


def cond_strings(conds):
    """Enclosing conditions as readable text; a negated branch (else / ifnot) is prefixed with `!`."""
    return [("" if pol else "!") + "( %s )" % c for _i, _k, c, pol in conds if c]


# --------------------------------------------------------------------------------------------- expression helpers
SAFE_CHARS = re.compile(r"^[0-9\s()+\-*/%&|^<>=!g]*$")


def _eval(text, env):
    if "**" in text:
        return None
    py = text.replace("&&", " and ").replace("||", " or ")
    py = re.sub(r"!(?!=)", " not ", py)
    py = py.replace("/", "//")
    try:
        return eval(py, {"__builtins__": {}}, env)      # noqa: S307 - input restricted to SAFE_CHARS by the callers
    except Exception:
        return None


def const_value(text):
    """Integer value of a constant expression (digits, operators, parentheses only), else None."""
    t = text.strip()
    if not t or not re.fullmatch(r"[0-9\s()+\-*/%&|^<>]*", t):
        return None
    v = _eval(t, {})
    return v if isinstance(v, int) else None


def split_top(text, sep):
    parts, depth, cur, i = [], 0, "", 0
    while i < len(text):
        ch = text[i]
        depth += (ch == "(") - (ch == ")")
        if depth == 0 and text.startswith(sep, i):
            parts.append(cur)
            cur, i = "", i + len(sep)
            continue
        cur += ch
        i += 1
    parts.append(cur)
    return parts


def eval_guard(cond_text, tok, value):
    """Evaluate cond with variable `tok` = value: True / False / None (not evaluable from that variable alone)."""
    t = cond_text.replace(tok, "g")
    if not SAFE_CHARS.match(t):
        return None
    r = _eval(t, {"g": value})
    return None if r is None else bool(r)


def apply_op(op, old, c, bits):
    """The value a write leaves behind (masked to `bits`), or None for an operator not modelled."""
    mask = (1 << bits) - 1
    if op == "=":
        return c & mask
    if op == "++":
        return (old + 1) & mask
    if op == "--":
        return (old - 1) & mask
    table = {"+=": old + c, "-=": old - c, "|=": old | c, "&=": old & c, "^=": old ^ c}
    return table[op] & mask if op in table else None


def closes_gate(cond, pol, tok, span, w):
    """Does write `w` (to the guard variable `tok`) leave the guard in a state that no longer admits the branch
    guarded by (cond, pol)?  Brute force over the guard's domain: every prior value that admits the branch must be
    sent to a value that does not.  A positive guard ignores conjuncts it cannot evaluate from `tok` alone (that can
    only miss a closing, never invent one); a negated guard must be fully evaluable."""
    if w["op"] in ("++", "--"):
        c = 0
    else:
        c = const_value(w["rhs"])
        if c is None:
            return False
    bits = min(span[2] - span[1], 16)
    domain = [0, 1] if bits <= 1 else (list(range(1 << bits)) if bits <= 8 else list(range(1024)) + [(1 << bits) - 1])
    mask = (1 << bits) - 1

    def entered(val):
        if pol:
            res = [r for r in (eval_guard(cj, tok, val) for cj in split_top(cond, "&&")) if r is not None]
            return all(res) if res else None
        r = eval_guard(cond, tok, val)
        return None if r is None else (not r)

    admitted = 0
    for prior in domain:
        e = entered(prior)
        if e is None:
            return False
        if not e:
            continue
        admitted += 1
        new = apply_op(w["op"], prior, c, bits)
        if new is None:
            return False
        e2 = entered(new & mask)
        if e2 is None or e2:
            return False
    return admitted > 0


# --------------------------------------------------------------------------------------------- classification
def rmw_kind(w, tok, rhs_reads_target):
    op = w["op"]
    if op in ("++", "--", "+=", "-="):
        return "counter"
    if op == "^=":
        return "toggle"
    if op in ("|=", "&="):
        return "bitmask"
    if op != "=":
        return "scale"
    if rhs_reads_target:
        r = re.sub(r"\s+", " ", w["rhs"]).strip()
        if re.fullmatch(r"\(? ?%s [+-] [0-9]+ ?\)?" % re.escape(tok), r):
            return "counter"
        if re.fullmatch(r"\(? ?%s [&|] .*" % re.escape(tok), r) or re.search(r"\( ?~", r):
            return "bitmask"
        return "self-referential"
    return "guard-reads-target"


def reset_before(w, prior):
    """Was the target assigned (a constant, or a copy of something else) earlier in the function, in a block that
    encloses this write?  Then a counter on it (`x = 0 ... x++`, `x = y ... x -= 8`) is scratch: its final value
    does not depend on what the frame held on entry."""
    ids = [c[0] for c in w["conds"]]
    for p in prior:
        if p["op"] == "=" and overlaps(p["span"], w["span"]) and not any(
                overlaps(s, w["span"]) for _t, f, s in var_tokens(p["rhs"]) if persistent(f)):
            pids = [c[0] for c in p["conds"]]
            if pids == ids[:len(pids)]:
                return True
    return False


def classify_scope(writes):
    """Give every persistent write of one function a class.  Returns those writes."""
    # random taint, in source order: a variable is tainted once a statement stores GetRandom (or a tainted variable)
    # in it.  Forward only: a later plain overwrite does not clear it, and a loop-carried use that sits textually
    # before the taint is not seen.
    tainted, taint_at = set(), {}
    for w in writes:
        taint_at[id(w)] = frozenset(tainted)           # the taint set that this statement's RHS and conditions read
        w["rhs_random"] = "GetRandom" in w["rhs"] or any(t in tainted for t, _f, _s in var_tokens(w["rhs"]))
        if w["rhs_random"]:
            tainted.add(w["target"])
    # the writes inside each branch (any depth), for the once-gate search
    inside = collections.defaultdict(list)
    for w in writes:
        for fid, _k, _c, _p in w["conds"]:
            inside[fid].append(w)

    out, prior = [], []
    for w in writes:
        toks = list(var_tokens(w["target"]))
        if not toks or not persistent(toks[0][1]):
            continue
        tok, fam, span = toks[0]
        w["span"], w["token"] = span, tok
        before = taint_at[id(w)]
        rhs_toks = list(var_tokens(w["rhs"]))
        conds = [(fid, k, c, p) for fid, k, c, p in w["conds"] if c]
        cond_toks = [(fid, k, c, p, list(var_tokens(c))) for fid, k, c, p in conds]

        cond_random = any("GetRandom" in c or any(t in before for t, _f, _s in tk) for _i, _k, c, _p, tk in cond_toks)
        rhs_reads_target = any(overlaps(s, span) for _t, f, s in rhs_toks if persistent(f))
        guard_reads_target = any(overlaps(s, span) for _i, _k, _c, _p, tk in cond_toks for _t, f, s in tk
                                 if persistent(f))

        once_via = None
        for fid, kind, ctext, pol, tk in cond_toks:
            if kind not in ("if", "else") or once_via:
                continue
            for gtok, gfam, gspan in tk:
                if not persistent(gfam) or gspan is None or once_via:
                    continue
                for cw in inside[fid]:
                    ct = list(var_tokens(cw["target"]))
                    if not ct or ct[0][0] != gtok:
                        continue
                    if cw is not w and cw["conds"][-1][0] != fid:       # must be unconditional within that branch
                        continue
                    if closes_gate(ctext, pol, gtok, gspan, cw):
                        once_via = (gtok, cw["line"])
                        break

        sub = None
        rhs_time = "GetTime" in w["rhs"]
        if tok in PROLOGUE_TOKENS or (tok == "General_FieldEntrance" and w["rhs"] == "10000"
                                      and [c for _i, _k, c, _p in conds] == ["General_LoadedGame == 1"]):
            cls = "prologue"
        elif overlaps(span, FE_SPAN):
            cls = "bytes 2-3"
            ctexts = [c for _i, _k, c, _p in conds]
            reads_fe = any("General_FieldEntrance" in c for c in ctexts)
            reads_sc = any("General_ScenarioCounter" in c for c in ctexts)
            k = const_value(w["rhs"])
            if k is not None and any(re.search(r"General_FieldEntrance == %d\b" % k, c) for c in ctexts):
                sub = "no-op"                          # rewrites to the value it just tested
            elif not ctexts:
                sub = "unconditional"
            else:
                sub = {(True, False): "FE-keyed", (False, True): "SC-keyed", (True, True): "FE+SC-keyed"}.get(
                    (reads_fe, reads_sc), "other-keyed")
        elif w["rhs_random"] or cond_random:
            cls = "random-gated"
            if w["rhs_random"]:
                # roll-once = the idiom `if var is unset: var = random()`: the guard reads the target's STORED value
                sub = "roll-once" if (guard_reads_target and w["target"] not in before) else "stores-random"
            else:
                sub = "random-branch"
        elif once_via:
            cls, sub = "once-gated", once_via[0]
        elif rhs_reads_target or guard_reads_target or w["op"] != "=":
            cls, sub = "read-modify-write", rmw_kind(w, tok, rhs_reads_target)
            if sub == "counter" and reset_before(w, prior):
                sub = "counter-reset"
        elif const_value(w["rhs"]) is not None:
            cls = "set"
        else:
            cls = "derived"
            sub = "time" if rhs_time else ("copy" if re.fullmatch(r"[A-Za-z0-9_]+", w["rhs"]) else "computed")
        w["cls"], w["sub"], w["guarded"] = cls, sub, bool(conds)
        out.append(w)
        prior.append(w)
    return out


def analyse_sections(secs, lang):
    """-> dict for one language section of one export.
    writes:      tier A, the classified writes of Main_Init and of the first Init function (the owner's scope)
    other_init:  tier B, class counts for the Init of every other entry Main_Init starts (supplementary)
    elsewhere:   tier C, random-gated / GetTime / accumulating-counter writes in every other function (supplementary)"""
    funcs = secs.get(lang, {})
    res = dict(found=False, writes=[], first_ref=None, problems=[], other_init={}, elsewhere=[], effects={}, calls=[])
    main = next((f for f in funcs.values() if f.name == "Main_Init"), None)
    if main is None:
        return res
    res["found"] = True
    for ln, raw in main.body:                  # tier D: Main_Init calls that change state OUTSIDE gEventGlobal
        for m in EFFECT_RE.finditer(strip_comment(raw)):
            res["effects"][m.group(1)] = res["effects"].get(m.group(1), 0) + 1
        for m in CALL_RE.finditer(strip_comment(raw)):
            res["calls"].append((m.group(1), ln))
    writes, inits, probs = parse_function(main)
    res["problems"] += [("Main_Init", ln, msg) for ln, msg in probs]
    for w in classify_scope(writes):
        w["scope"] = "Main_Init"
        res["writes"].append(w)
    # the first Init call whose function exists in the export (entries 251-254 are runtime team slots with no code here)
    skipped = 0
    first = None
    for ini in inits:
        if (ini["entry"], ini["tag"]) in funcs:
            first = ini
            break
        skipped += 1
    scoped = {id(main)}
    if first is not None:
        fn = funcs[(first["entry"], first["tag"])]
        res["first_ref"] = dict(call=first["call"], entry=first["entry"], tag=first["tag"], line=first["line"],
                                func=fn.name, skipped=skipped)
        scoped.add(id(fn))
        fw, _i, fprobs = parse_function(fn)
        res["problems"] += [(fn.name, ln, msg) for ln, msg in fprobs]
        for w in classify_scope(fw):
            w["scope"] = fn.name
            res["writes"].append(w)
    elif inits:
        res["first_ref"] = dict(call=inits[0]["call"], entry=inits[0]["entry"], tag=inits[0]["tag"],
                                line=inits[0]["line"], func=None, skipped=skipped)
    seen = {(first["entry"], first["tag"])} if first else set()
    for ini in inits:
        key = (ini["entry"], ini["tag"])
        fn = funcs.get(key)
        if key in seen or fn is None:
            continue
        seen.add(key)
        scoped.add(id(fn))
        ow, _i, _p = parse_function(fn)
        for w in classify_scope(ow):
            res["other_init"][w["cls"]] = res["other_init"].get(w["cls"], 0) + 1
    for fn in funcs.values():
        if id(fn) in scoped:
            continue
        ew, _i, _p = parse_function(fn)
        for w in classify_scope(ew):
            kind = ("random-gated" if w["cls"] == "random-gated" else "time" if w["sub"] == "time"
                    else "counter" if w["sub"] == "counter" else None)
            if kind:
                res["elsewhere"].append((fn.name, w["line"], w["token"], kind))
    return res


def signature(w):
    return (w["token"], w["op"], re.sub(r"\s+", " ", w["rhs"]), w["cls"])


# --------------------------------------------------------------------------------------------- driver
def load_manifest(path):
    m = {}
    if os.path.isfile(path):
        for ln in open(path, encoding="utf-8"):
            p = ln.rstrip("\r\n").split("\t")
            if len(p) >= 3:
                m[p[0]] = (int(p[1]), p[2])
    return m


def run(exports, manifest, compare_langs=False):
    man = load_manifest(manifest)
    files = sorted((f for f in os.listdir(exports) if re.fullmatch(r"test2_\d+\.txt", f)),
                   key=lambda s: int(re.findall(r"\d+", s)[0]))
    fields, lang_diff = [], []
    for fn in files:
        lines = open(os.path.join(exports, fn), encoding="utf-8", errors="replace").read().split("\n")
        secs = split_sections(lines)
        r = analyse_sections(secs, "us")
        fid, name = man.get(fn, (None, "?"))
        fields.append(dict(
            file=fn, field=fid, name=name, found=r["found"], first_ref=r["first_ref"], problems=r["problems"],
            other_init=r["other_init"], elsewhere=r["elsewhere"], effects=r["effects"], calls=r["calls"],
            writes=[dict(scope=w["scope"], line=w["line"], token=w["token"], target=w["target"], op=w["op"],
                         rhs=w["rhs"], cls=w["cls"], sub=w["sub"], guarded=w["guarded"], embedded=w["embedded"],
                         conds=cond_strings(w["conds"])) for w in r["writes"]]))
        if compare_langs:
            base = sorted(signature(w) for w in r["writes"])
            for lang in secs:
                if lang != "us":
                    o = analyse_sections(secs, lang)
                    if o["found"] and sorted(signature(w) for w in o["writes"]) != base:
                        lang_diff.append((fn, fid, name, lang))
    return fields, lang_diff


def cite(rec, w):
    return "%s:%d" % (rec["file"], w["line"])


def summarise(fields, lang_diff, compare_langs, out=sys.stdout):
    def P(*a):
        print(*a, file=out)

    P("fields scanned: %d (Main_Init not found: %d)" % (len(fields), sum(1 for f in fields if not f["found"])))
    probs = [(f["file"], p) for f in fields for p in f["problems"]]
    P("parse problems: %d%s" % (len(probs), "" if not probs else "  e.g. " + str(probs[:3])))
    wr = [(f, w) for f in fields for w in f["writes"]]
    P("persistent write statements: %d (Main_Init %d, first Init function %d)" % (
        len(wr), sum(1 for _f, w in wr if w["scope"] == "Main_Init"),
        sum(1 for _f, w in wr if w["scope"] != "Main_Init")))

    allcls = ["prologue"] + CLASSES
    P("\nwrite statements by class:")
    c = collections.Counter(w["cls"] for _f, w in wr)
    for k in allcls:
        P("  %-18s %6d" % (k, c.get(k, 0)))

    byfield = collections.defaultdict(set)
    for f, w in wr:
        byfield[f["file"]].add(w["cls"])
    P("\nfields by class (a field counts once per class it has; the classes overlap):")
    for k in allcls:
        P("  %-18s %5d fields" % (k, sum(1 for s in byfield.values() if k in s)))
    real = {k: s - {"prologue"} for k, s in byfield.items()}
    P("  fields with ONLY the stock prologue: %d" % sum(1 for f in fields if not real.get(f["file"])))
    P("  fields with at least one write beyond the prologue: %d" % sum(1 for s in real.values() if s))
    P("  of those, only `set` writes: %d" % sum(1 for s in real.values() if s == {"set"}))
    P("  of those, any class other than `set`: %d" % sum(1 for s in real.values() if s - {"set"}))
    order = ["random-gated", "bytes 2-3", "read-modify-write", "once-gated", "derived", "set"]
    top = collections.Counter(next(k for k in order if k in s) for s in real.values() if s)
    P("  each of those fields once, under its highest-concern class %s: %s" % (
        " > ".join(order), {k: top.get(k, 0) for k in order}))

    P("\nscope split, fields by class (Main_Init | first Init function):")
    for k in allcls:
        a = len({f["file"] for f, w in wr if w["cls"] == k and w["scope"] == "Main_Init"})
        b = len({f["file"] for f, w in wr if w["cls"] == k and w["scope"] != "Main_Init"})
        P("  %-18s %5d | %d" % (k, a, b))

    P("\nsub-classes (write statements; fields):")
    for k in ["bytes 2-3", "random-gated", "once-gated", "read-modify-write", "set", "derived"]:
        sc, sf = collections.Counter(), collections.defaultdict(set)
        for f, w in wr:
            if w["cls"] == k:
                key = w["sub"]
                if k == "set":
                    key = "guarded" if w["guarded"] else "unguarded"
                elif k == "once-gated":
                    key = "guard is a named word" if not key.startswith("VAR") else "guard is a flag/var"
                sc[key] += 1
                sf[key].add(f["file"])
        P("  %-18s %s" % (k, {key: "%d / %d" % (sc[key], len(sf[key])) for key in sc}))

    P("\nnon-prologue write signatures shared by the most fields (token, op, rhs, class):")
    sig = collections.defaultdict(set)
    for f, w in wr:
        if w["cls"] != "prologue":
            sig[signature(w)].add(f["file"])
    for s, fs in sorted(sig.items(), key=lambda kv: -len(kv[1]))[:14]:
        P("  %4d fields  %s" % (len(fs), s))

    for cls in ("random-gated", "bytes 2-3"):
        by = collections.OrderedDict()
        for f, w in wr:
            if w["cls"] == cls:
                by.setdefault(f["file"], (f, []))[1].append(w)
        P("\n== %s: %d fields, %d write statements ==" % (cls, len(by), sum(len(v[1]) for v in by.values())))
        P("| field | name | export cite | what the statements are |")
        for fn, (f, ws) in sorted(by.items(), key=lambda kv: (kv[1][0]["field"] or 0)):
            kinds = collections.Counter(w["sub"] for w in ws)
            P("| %s | %s | %s:%s | %s |" % (f["field"], f["name"], f["file"], ", ".join(str(w["line"]) for w in ws),
                                           ", ".join("%s x%d" % (k, n) for k, n in kinds.items())))
    P("\n== time-derived persistent writes (GetTime) in the scoped functions ==")
    for f, w in wr:
        if w["sub"] == "time":
            P("  field %s | %s | %s:%d  %s = %s" % (f["field"], f["name"], f["file"], w["line"], w["token"], w["rhs"]))

    P("\n== accumulating counters in the scoped functions (compound write, no earlier reset) ==")
    for f in fields:
        ws = [w for w in f["writes"] if w["cls"] == "read-modify-write" and w["sub"] == "counter"]
        if ws:
            P("  field %s | %s | %s" % (f["field"], f["name"], ", ".join(
                "%s:%d %s%s" % (f["file"], w["line"], w["token"], w["op"]) for w in ws[:4])))
    P("  (none above means none)")

    P("\n== toggles and self-referential updates in the scoped functions (not safe to replay on a frame that already ran them) ==")
    for f in fields:
        for w in f["writes"]:
            if w["cls"] == "read-modify-write" and w["sub"] in ("toggle", "self-referential"):
                P("  field %s | %s | %s:%d  %s %s %s   [%s]%s" % (
                    f["field"], f["name"], f["file"], w["line"], w["token"], w["op"], w["rhs"][:40], w["sub"],
                    "  if " + " && ".join(w["conds"])[:60] if w["conds"] else "  (unconditional)"))

    sc = [(f, w) for f in fields for w in f["writes"] if w["token"] == "General_ScenarioCounter"]
    def unsatisfiable(w):                  # a positive `SC < N` and a positive `SC > N` for the same N
        pos = [c for c in w["conds"] if not c.startswith("!")]
        lows = {m.group(1) for c in pos for m in re.finditer(r"General_ScenarioCounter < (\d+)", c)}
        highs = {m.group(1) for c in pos for m in re.finditer(r"General_ScenarioCounter > (\d+)", c)}
        return bool(lows & highs)
    unsat = [(f, w) for f, w in sc if unsatisfiable(w)]
    btn = [(f, w) for f, w in sc if any("IsButton" in c for c in w["conds"]) and (f, w) not in unsat]
    P("\n== ScenarioCounter (bytes 0-1) writes in the scoped functions: %d statements, %d fields ==" % (
        len(sc), len({f["file"] for f, _w in sc})))
    P("  behind an unsatisfiable `SC < N and SC > N`: %d" % len(unsat))
    P("  set down while IsButton(8) is held: %d (fields %s)" % (len(btn), ", ".join(str(f["field"]) for f, _w in btn)))
    P("  the rest (a floor snap, a step, or an unconditional store): %d" % (len(sc) - len(unsat) - len(btn)))
    for f, w in sc:
        if not w["conds"]:
            P("    unconditional: field %s | %s | %s:%d  = %s" % (f["field"], f["name"], f["file"], w["line"], w["rhs"]))

    P("\n== Loop-type functions with an accumulating counter (outside the scope, listed because the pin's rationale quotes one) ==")
    for f in fields:
        hits = sorted({(e[0], e[1], e[2]) for e in f["elsewhere"]
                       if e[3] == "counter" and re.match(r"Code\d+_Loop$", e[0])})
        if hits:
            P("  field %s | %s | %s" % (f["field"], f["name"], ", ".join(
                "%s %s:%d %s" % (fn, f["file"], ln, tok) for fn, ln, tok in hits[:2])))

    P("\nfirst Init function resolution:")
    P("  Main_Init starts no Init call: %d" % sum(1 for f in fields if f["found"] and f["first_ref"] is None))
    P("  no started entry has a function in the export: %d" % sum(
        1 for f in fields if f["first_ref"] and f["first_ref"]["func"] is None))
    P("  first call kind: %s" % dict(collections.Counter(f["first_ref"]["call"] for f in fields if f["first_ref"])))
    P("  first resolvable call is not the first call (entries 251-254, runtime team slots, skipped): %d" % sum(
        1 for f in fields if f["first_ref"] and f["first_ref"].get("skipped")))
    P("  first call tag != 0: %d" % sum(1 for f in fields if f["first_ref"] and f["first_ref"]["tag"] != 0))
    oi = [f for f in fields if f["other_init"]]
    P("\nTIER D, Main_Init calls that change state outside gEventGlobal (fields containing each call):")
    for name in sorted({n for f in fields for n in f["effects"]}):
        P("  %-26s %4d fields" % (name, sum(1 for f in fields if name in f["effects"])))
    P("  fields with any of them: %d (%s)" % (sum(1 for f in fields if f["effects"]),
                                          ", ".join(str(f["field"]) for f in fields if f["effects"])))
    P("  Main_Init launches another script (RunScript*/RunSharedScript, target not followed): %d fields, %d calls" % (
        sum(1 for f in fields if f["calls"]), sum(len(f["calls"]) for f in fields)))
    P("\nTIER B, the Init of every OTHER entry Main_Init starts: %d fields have persistent writes" % len(oi))
    tb = collections.Counter()
    for f in oi:
        for k, n in f["other_init"].items():
            tb[k] += n
    P("  statements by class: %s" % dict(tb))
    P("  fields by class: %s" % {k: sum(1 for f in oi if k in f["other_init"]) for k in tb})
    ew = [(f, e) for f in fields for e in f["elsewhere"]]
    P("TIER C, every other function (Loop, Range, Reinit, talk handlers, ...):")
    for kind in ("random-gated", "time", "counter"):
        sel = [(f, e) for f, e in ew if e[3] == kind]
        byfn = collections.Counter(re.sub(r"\d+", "N", e[0]) for _f, e in sel)
        P("  %-13s %4d fields, %5d statements   by function name: %s" % (
            kind, len({f["file"] for f, _e in sel}), len(sel), dict(byfn.most_common(6))))
    P("  random-gated / GetTime fields: " + "; ".join(sorted({"%s %s" % (f["field"], f["name"]) for f, e in ew
                                                           if e[3] in ("random-gated", "time")})))
    if compare_langs:
        P("\nfields whose non-us section classifies differently from the us section: %d" % len(lang_diff))
        for fn, fid, name, lang in lang_diff[:40]:
            P("  %s field %s %s [%s]" % (fn, fid, name, lang))


SELFTEST_EXPORT = """#HW language us
#HW newentry 0
#HW newfunction 0
Function Main_Init
    set VAR_GenBool_191 = 0
    set VARL_GenUInt8_500 = 7
    if ( General_ScenarioCounter >= 100 ) {
        set VARL_GenUInt8_501 = 1
    }
    set VARL_GenUInt8_502 += 1
    set VARL_GenUInt8_503 = 0
    set VARL_GenUInt8_503++
    set VARL_GenUInt16_504 |= 4
    if ( VARL_GenBool_600 == 0 ) {
        set VARL_GenBool_600 = 1
        set VARL_GenUInt8_505 = 9
    }
    if ( VARL_GenBool_601 == 0 ) {
        set VARL_GenUInt8_506 = 2
    }
    if ( VARL_GenUInt8_510 == 0 ) {
        set VARL_GenUInt8_510 = GetRandom
    }
    set VARL_GenUInt8_511 = ( GetRandom % 4 )
    set VAR_LocUInt8_0 = GetRandom
    if ( VAR_LocUInt8_0 < 128 ) {
        set VARL_GenUInt8_512 = 1
    }
    set VARL_GenUInt8_513 = VARL_GenUInt8_514
    if ( General_FieldEntrance == 3 ) {
        set General_FieldEntrance = 3
    }
    set VARL_GenBool_700 ^= 1
    set VAR_GlobUInt8_5 = 3
    switchex 2 ( General_FieldEntrance ) {
    case 1:
        set VARL_GenUInt8_520 = 4
        break
    default:
        set VARL_GenUInt8_521 = 5
        break
    }
    InitCode( 2, 0 )
    return
"""

# line number (within SELFTEST_EXPORT) -> expected (class, sub); sub None = not checked
SELFTEST_EXPECT = {
    5: ("prologue", None), 6: ("set", "unguarded"), 8: ("set", "guarded"), 10: ("read-modify-write", "counter"),
    12: ("read-modify-write", "counter-reset"), 13: ("read-modify-write", "bitmask"),
    15: ("once-gated", None), 16: ("once-gated", None), 19: ("set", "guarded"),
    22: ("random-gated", "roll-once"), 24: ("random-gated", "stores-random"), 27: ("random-gated", "random-branch"),
    29: ("derived", "copy"), 31: ("bytes 2-3", "no-op"), 33: ("read-modify-write", "toggle"),
    37: ("set", "guarded"), 40: ("set", "guarded"),
}


def selftest():
    """Break-it check: every class must fire on a synthetic Main_Init, and the negative controls must not."""
    secs = split_sections(SELFTEST_EXPORT.split("\n"))
    r = analyse_sections(secs, "us")
    got = {w["line"]: (w["cls"], ("guarded" if w["guarded"] else "unguarded") if w["cls"] == "set" else w["sub"])
           for w in r["writes"]}
    bad = []
    for ln, (cls, sub) in SELFTEST_EXPECT.items():
        g = got.get(ln)
        if g is None or g[0] != cls or (sub is not None and g[1] != sub):
            bad.append("line %d expected %s/%s got %s" % (ln, cls, sub, g))
    if 34 in got:
        bad.append("transient VAR_Glob write was counted: %s" % (got[34],))
    for b in bad:
        print("SELFTEST FAIL:", b)
    print("selftest: %s (%d statements checked)" % ("FAILED" if bad else "ok", len(SELFTEST_EXPECT) + 1))
    return 1 if bad else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("exports", nargs="?", default=DEFAULT_EXPORTS, help="directory of test2_N.txt (default %(default)s)")
    ap.add_argument("--manifest", default=DEFAULT_MANIFEST, help="field-manifest.tsv: HW index -> field id, name")
    ap.add_argument("--json", metavar="PATH", help="also write one record per field as JSON")
    ap.add_argument("--compare-langs", action="store_true", help="also classify the non-us sections, report differences")
    ap.add_argument("--selftest", action="store_true", help="run the synthetic classifier check and exit")
    a = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if a.selftest:
        return selftest()
    if not os.path.isdir(a.exports):
        print("exports directory not found: %s" % a.exports, file=sys.stderr)
        return 2
    fields, lang_diff = run(a.exports, a.manifest, a.compare_langs)
    summarise(fields, lang_diff, a.compare_langs)
    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump(fields, fh, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
