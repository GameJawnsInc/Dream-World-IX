"""CHOICE census over all ~818 real FF9 field scripts -- the F3 dialogue-lockstep CHOICES lane.

Byte-grounded: decodes every field's `.eb` live from the Steam install (UnityPy, via the kit's
`extract.EventBundle`) and walks RAW OPCODES + expression token streams -- never a text transcript
(the CENSUS LAW). Deterministic: fields iterated in sorted id order; no randomness; re-runnable.

Run from the kit dir:
    cd ff9mapkit && python ../studies/field-coop/dialogue-census/choice_census.py
    (add  --dump-tables  to also write choices_census_output.txt next to this script)

THE CHOICE IDIOM (grounded in ff9mapkit/content/choice.py + Memoria EBin.cs, confirmed vs field 300):
  * The chosen row index is carried by the expression token  B_SYSVAR (0x7A) with code 9  ->
    EventEngine.GetSysvar(9) -> ETb.GetChoose() (0-based row). In bytes: `7A 09` inside an expr stream.
  * The choice ROWS live in the field's `.mes` TEXT as an inline `[CHOO]` tag; `[PCHC=n,cancel]` /
    `[PCHM=n,cancel]` (hide) tags set count/cancel/default. Optional setup opcode EnableDialogChoices
    (0x7C) presets the availability mask + default-highlighted row.
  * A script CONSUMES the pick three ways, all detected here from the `.eb`:
      SWITCH   `05{7A 09 7F}` then a switch (0x0B/0x06/0x0D)   -- one read, one arm per row
      IF       `05{7A 09 7D k 20 ...}` then JMP_FALSE 0x02      -- one read per compared row
      STORE    `05{<var> 7A 09 2C ...}`  (an assign op 44..69)  -- the pick saved into a variable
"""
from __future__ import annotations

import collections
import sys
from pathlib import Path

_KIT = Path(__file__).resolve().parents[3] / "ff9mapkit"
if str(_KIT) not in sys.path:
    sys.path.insert(0, str(_KIT))

from ff9mapkit import extract                       # noqa: E402
from ff9mapkit.extract import FIELD_BY_ID           # noqa: E402
from ff9mapkit.eb import disasm                     # noqa: E402
from ff9mapkit.eb.model import EbScript             # noqa: E402
from ff9mapkit.eb._optables import OP_ARG_COUNT     # noqa: E402

# --- opcode / token constants (all from the kit's own tables) ---
SYSVAR_TOK = 0x7A          # B_SYSVAR expression token
CHOICE_CODE = 9            # GetSysvar(9) == GetChoose()
ENABLE_CHOICES = 0x7C      # EnableDialogChoices (setup: avail mask + default)
EXPR_STMT = 0x05           # standalone expression statement
JMP_FALSE, JMP_TRUE = 0x02, 0x03
SWITCH_OPS = (0x06, 0x0B, 0x0D)
OP_FIELD, OP_ADDITEM, OP_MENU, OP_AICON = 0x2B, 0x48, 0x75, 0xD7
WINDOW_OPS = (0x1F, 0x20, 0x95, 0x96)   # WindowSync/Async(+Ex): a window open; winATE flag = bit 64
ASSIGN_OPS = frozenset(range(44, 70))   # B_LET .. B_OR_LET_E  (an expression that WRITES a var)
INCDEC_OPS = frozenset(range(4, 12))    # post/pre ++/-- on a var
CMP_OPS = {0x18: "<", 0x19: ">", 0x1a: "<=", 0x1b: ">=", 0x20: "==", 0x21: "!=", 0x22: "==E", 0x23: "!=E"}
# variable-token SOURCE (token & 3): 0=Global(save,MIRRORED) 1=Map(transient) 2=Instance(transient) 3=Null
SRC_NAME = {0: "GLOB", 1: "MAP", 2: "INST", 3: "NULL"}


# ----------------------------------------------------------------- expression walker ---
def walk_expr(raw, pos):
    """Decode one expression token stream -> (list of (op, operand_tuple), new_pos). Mirrors
    disasm.read_expr's exact byte-walk so operand widths match the engine."""
    toks = []
    while True:
        o = raw[pos]; pos += 1
        isconst = o in (0x7D, 0x7E)
        isvar = o >= 0xC0 or o in (0x29, 0x5F, 0x78, 0x79, 0x7A)
        if not isconst and not isvar:
            toks.append((o, ()))
            if o == 0x7F:
                break
            continue
        if o == 0x7E:
            a = (raw[pos] | raw[pos + 1] << 8 | raw[pos + 2] << 16 | raw[pos + 3] << 24,); pos += 4
        elif o == 0x7D:
            a = (raw[pos] | raw[pos + 1] << 8,); pos += 2
        elif o == 0x78:
            a = (raw[pos], raw[pos + 1]); pos += 2
        elif o in (0x79, 0x7A, 0x29, 0x5F):
            a = (raw[pos],); pos += 1
        elif o >= 0xE0:
            a = (raw[pos] | raw[pos + 1] << 8,); pos += 2
        else:
            a = (raw[pos],); pos += 1
        toks.append((o, a))
    return toks, pos


def expr_streams(raw, ins):
    """List of token-lists for each EXPRESSION operand of *ins* (immediate operands skipped)."""
    pos = ins.off
    op = raw[pos]; pos += 1
    if op == 0xFF:
        op = 0x100 | raw[pos]; pos += 1
    ac = OP_ARG_COUNT[op] if op < len(OP_ARG_COUNT) else 0
    arg_flag = 0
    if op >= 0x10 and ac != 0:
        arg_flag = raw[pos]; pos += 1
    if op == 0x05:
        arg_flag = 1
    if ac < 0:
        ac = raw[pos]; pos += 1
        if op == 0x0D:
            ac |= raw[pos] << 8; pos += 1
        if op == 0x06:
            ac = 1 + 2 * ac
        elif op in (0x0B, 0x0D):
            ac = 2 + ac
    out = []
    for i in range(ac):
        if arg_flag & (1 << i):
            toks, pos = walk_expr(raw, pos)
            out.append(toks)
        else:
            pos += disasm.argsize(op, i)
    return out


def reads_choice(toks):
    return any(o == SYSVAR_TOK and a and a[0] == CHOICE_CODE for o, a in toks)


def write_target_source(toks):
    """If this stream WRITES a var (has an assign/incdec op), return the source (0..3) of the FIRST
    var-token (the assignment target is pushed first). Else None. GetChoose (0x7A) is a System read,
    never a var-token >= 0xC0, so it is never mistaken for the target."""
    if not any(o in ASSIGN_OPS or o in INCDEC_OPS for o, _ in toks):
        return None
    for o, a in toks:
        if o >= 0xC0:
            src = o & 3
            is_scenario = (o == 0xDC and a and a[0] == 0)   # Global.UInt16[0] == ScenarioCounter
            return (src, is_scenario)
    return None


def cmp_const(toks):
    """(cmp_op, k) if the stream compares GetChoose() to a constant, else (None, None)."""
    seen_choice = False
    k = None
    for o, a in toks:
        if o == SYSVAR_TOK and a and a[0] == CHOICE_CODE:
            seen_choice = True
        elif seen_choice and o == 0x7D and k is None:
            k = a[0]
        elif seen_choice and o in CMP_OPS:
            return CMP_OPS[o], k
    return None, None


# ----------------------------------------------------------------- consequence scan ---
def region_consequence(instrs, lo, hi, raw):
    """Classify writes/effects in the byte region [lo, hi) (a dispatch's option bodies)."""
    r = collections.Counter()
    for ins in instrs:
        if not (lo <= ins.off < hi):
            continue
        if ins.op == OP_FIELD:
            r["field"] += 1
        elif ins.op == OP_ADDITEM:
            r["additem"] += 1
        elif ins.op == OP_MENU:
            r["menu"] += 1
        for t in expr_streams(raw, ins):
            if reads_choice(t):
                r["nested_choice"] += 1
            w = write_target_source(t)
            if w is not None:
                src, is_scn = w
                r[SRC_NAME.get(src, "NULL")] += 1
                if is_scn:
                    r["scenario"] += 1
    return r


def free_class(r):
    """F3 consequence bucket for a delimited dispatch region (its option-body arms).
      DIV_ONLY   = writes MAP/INST transient state and NO Global flag -- the pick drives only
                   per-visit field-local state (outside the gEventGlobal mirror; wiped on field reload)
      DIV_GLOB   = writes MAP/INST transient state AND a Global flag -- the STORY still mirrors
                   (the GLOB write reaches the guest); only the transient presentation can differ
      GLOB_only  = writes only Global (save) flags -- mirrored -> guest pick converges at next field load
      WARP       = only a Field() transition -- host-authoritative via follow-warp; no local flag
      ITEM_MENU  = only an AddItem/Menu open -- guest-local bag/menu; reverted by the exit ramp
      INERT      = no write/warp/item/menu at all -- pure reply text / SFX -> nothing to diverge"""
    trans = r["MAP"] or r["INST"]
    if trans and r["GLOB"]:
        return "DIV_GLOB"
    if trans:
        return "DIV_ONLY"
    if r["GLOB"]:
        return "GLOB_only"
    if r["field"]:
        return "WARP"
    if r["additem"] or r["menu"]:
        return "ITEM_MENU"
    return "INERT"


def _tally_attrs(out, r):
    """OVERLAPPING arm attributes (a site can have several): does any arm warp / grant an item /
    open a menu / advance the ScenarioCounter?"""
    if r["field"]:
        out["site_attr"]["warp"] += 1
    if r["additem"]:
        out["site_attr"]["item"] += 1
    if r["menu"]:
        out["site_attr"]["menu"] += 1
    if r["scenario"]:
        out["site_attr"]["scenario"] += 1
    if r["GLOB"]:
        out["site_attr"]["any_glob"] += 1
    if r["MAP"] or r["INST"]:
        out["site_attr"]["any_transient"] += 1


# ----------------------------------------------------------------- the census ---
def census():
    bundle = extract.EventBundle()
    ids = sorted(FIELD_BY_ID)

    out = {
        "n_fields": len(ids),
        "fields_with_choice": 0,
        "reads_total": 0,
        "read_host_op": collections.Counter(),      # which opcode hosts the GetChoose token
        "read_class": collections.Counter(),        # SWITCH / IF / STORE / OTHER
        "store_scope": collections.Counter(),       # STORE target scope
        "if_cmp": collections.Counter(),            # cmp op used in IF reads
        "enable_total": 0,
        "enable_default": collections.Counter(),
        "enable_mask_bit15": 0,                      # mask with bit15 set (sign-extend degeneracy risk)
        "enable_default_ge_16": 0,
        "switch_sites": 0,
        "switch_rows": collections.Counter(),        # rows -> #switch sites
        "ifchain_sites": 0,
        "ifchain_rows": collections.Counter(),       # rows -> #if-chain sites
        "site_class": collections.Counter(),         # F3 bucket per branch site (switch + if-chain)
        "site_class_by_kind": collections.defaultdict(collections.Counter),
        "site_attr": collections.Counter(),           # OVERLAPPING arm attributes: warp/item/menu/scenario
        "store_class": collections.Counter(),        # F3 bucket per STORE read (by target scope)
        "per_field_reads": collections.Counter(),
        "menu_arg0": collections.Counter(),          # Menu(0x75) first-arg distribution (softlock family)
        "menu_party_fields": set(),                  # fields that open Menu(4,*) party-change
        "funcs_with_choice": 0,
        "funcs_multi_site": 0,                        # >1 branch site in one func (sequence/nesting candidate)
        "nested_sites": 0,                            # a branch site whose arms contain another GetChoose
        "ate_choice_funcs": 0,                        # choice read in a func that also has AICON (ATE marker)
        "winate_choice": 0,                           # a window opened with the winATE (64) flag near a choice
        "big_menu_examples": [],                      # (field, entry, tag, rows) for rows>=10 switch sites
        "fields_div_only": set(),                     # fields with >=1 DIV_ONLY site or divergent STORE
        "fields_all_safe": 0,                         # fields whose EVERY choice consequence is story-safe
        "big_menu_tag": collections.Counter(),        # entry-func tag of the >=10-row switch menus
    }
    field_div = collections.defaultdict(bool)         # fid -> has a purely-transient (no-glob) consequence

    for fid in ids:
        eb = bundle.eb_for_id(fid)
        if not eb:
            continue
        try:
            scr = EbScript.from_bytes(eb)
        except Exception:
            continue
        raw = scr.data
        field_reads = 0
        field_has_party_menu = False

        for e in scr.entries:
            if e.empty:
                continue
            entry_has_aicon = any(
                ins.op == OP_AICON for f in e.funcs for ins in scr.instrs(f)
            )
            for f in e.funcs:
                instrs = list(scr.instrs(f))
                func_sites = 0
                func_has_choice = False
                func_has_aicon = any(ins.op == OP_AICON for ins in instrs)
                # collect IF-branch reads for per-function chaining
                if_reads = []      # (order_idx, k, body_lo, body_hi)
                for idx, ins in enumerate(instrs):
                    if ins.op == ENABLE_CHOICES:
                        out["enable_total"] += 1
                        d = ins.imm(1)
                        m = ins.imm(0)
                        if d is not None:
                            out["enable_default"][d] += 1
                            if d >= 16:
                                out["enable_default_ge_16"] += 1
                        if m is not None and (m & 0x8000):
                            out["enable_mask_bit15"] += 1
                    if ins.op in WINDOW_OPS:
                        fl = ins.imm(1)
                        # a winATE (bit 64) window near a choice read is an ATE menu
                        if fl is not None and (fl & 64):
                            # cheap: check the same function for a choice read
                            if any(reads_choice(t) for j in instrs for t in expr_streams(raw, j)):
                                pass  # counted below via func-level
                    streams = expr_streams(raw, ins)
                    if not any(reads_choice(t) for t in streams):
                        continue
                    # this instruction hosts >=1 GetChoose token
                    func_has_choice = True
                    out["read_host_op"][disasm.op_name(ins.op)] += 1
                    n_reads = sum(1 for t in streams if reads_choice(t))
                    out["reads_total"] += n_reads
                    field_reads += n_reads

                    # classify (use the FIRST choice-bearing stream of this instr)
                    ctoks = next(t for t in streams if reads_choice(t))
                    nxt = instrs[idx + 1] if idx + 1 < len(instrs) else None
                    w = write_target_source(ctoks)
                    if w is not None:                       # STORE: pick saved into a var
                        src = w[0]
                        out["read_class"]["STORE"] += 1
                        out["store_scope"][SRC_NAME.get(src, "NULL")] += 1
                        out["store_class"]["GLOB_only" if src == 0 else "DIVERGENT"] += 1
                        if src != 0:
                            field_div[fid] = True
                    elif nxt is not None and nxt.op in SWITCH_OPS:   # SWITCH dispatch
                        out["read_class"]["SWITCH"] += 1
                        out["switch_sites"] += 1
                        func_sites += 1
                        si = nxt.switch()
                        rows = len([x for x in si.edges if not x.is_default]) if si else 0
                        out["switch_rows"][rows] += 1
                        if si:
                            # TIGHT per-arm delimitation: each CASE arm = [target, next distinct edge
                            # target above it) -- so a far-jumping `default` (a shared cleanup handler)
                            # never bleeds unrelated code into the region. The default arm is excluded
                            # (it is the out-of-range/exit path, ~never a story write, and its span is
                            # the one prone to over-reach). Bodies unioned into one counter.
                            bounds = sorted(set(x.target for x in si.edges) | {f.abs_end})
                            r = collections.Counter()
                            for ct in sorted(set(x.target for x in si.edges if not x.is_default)):
                                hi = next((b for b in bounds if b > ct), f.abs_end)
                                r.update(region_consequence(instrs, ct, hi, raw))
                            cls = free_class(r)
                            out["site_class"][cls] += 1
                            out["site_class_by_kind"]["switch"][cls] += 1
                            _tally_attrs(out, r)
                            if cls == "DIV_ONLY":
                                field_div[fid] = True
                            if r["nested_choice"]:
                                out["nested_sites"] += 1
                            if rows >= 10:
                                out["big_menu_tag"][f.tag] += 1
                                if len(out["big_menu_examples"]) < 25:
                                    out["big_menu_examples"].append((fid, e.index, f.tag, rows))
                    elif nxt is not None and nxt.op in (JMP_FALSE, JMP_TRUE):   # IF compare
                        out["read_class"]["IF"] += 1
                        cop, k = cmp_const(ctoks)
                        out["if_cmp"][cop or "?"] += 1
                        skip = nxt.imm(0) or 0
                        body_lo, body_hi = nxt.end, nxt.end + skip
                        if_reads.append((idx, k if k is not None else -1, body_lo, body_hi))
                    else:
                        out["read_class"]["OTHER"] += 1

                # --- group IF reads into if-chain SITES (per function) ---
                if if_reads:
                    # Group IF reads into per-menu SITES (APPROXIMATE -- the .eb has no window marker):
                    # a new menu starts when a PARSED k==0 handler reappears after the current group
                    # already has rows (every menu has a row-0 arm). Unparsed (k=-1, a compound cond)
                    # and range (`<`) reads just extend the current group. Labelled approximate in the doc.
                    site_bodies = []           # list of {rows, bodies}
                    cur = None
                    for (idx, k, lo, hi) in if_reads:
                        if cur is None or (k == 0 and cur["rows"] > 0):
                            cur = {"rows": 0, "bodies": []}
                            site_bodies.append(cur)
                        cur["rows"] += 1
                        cur["bodies"].append((lo, hi))
                    for site in site_bodies:
                        out["ifchain_sites"] += 1
                        func_sites += 1
                        out["ifchain_rows"][site["rows"]] += 1
                        r = collections.Counter()
                        nested = 0
                        for (lo, hi) in site["bodies"]:
                            rr = region_consequence(instrs, lo, hi, raw)
                            r.update(rr)
                            nested += rr["nested_choice"]
                        cls = free_class(r)
                        out["site_class"][cls] += 1
                        out["site_class_by_kind"]["ifchain"][cls] += 1
                        _tally_attrs(out, r)
                        if cls == "DIV_ONLY":
                            field_div[fid] = True
                        if nested:
                            out["nested_sites"] += 1

                # Menu(0x75) softlock-family census (all funcs, not just choice funcs)
                for ins in instrs:
                    if ins.op == OP_MENU:
                        a0 = ins.imm(0)
                        if a0 is not None:
                            out["menu_arg0"][a0] += 1
                            if a0 == 4:
                                field_has_party_menu = True

                if func_has_choice:
                    out["funcs_with_choice"] += 1
                    if func_sites > 1:
                        out["funcs_multi_site"] += 1
                    if func_has_aicon:
                        out["ate_choice_funcs"] += 1

        if field_reads:
            out["fields_with_choice"] += 1
            out["per_field_reads"][fid] = field_reads
        if field_has_party_menu:
            out["menu_party_fields"].add(fid)
        if field_reads and field_div[fid]:
            out["fields_div_only"].add(fid)

    out["fields_all_safe"] = out["fields_with_choice"] - len(out["fields_div_only"])
    return out


# ----------------------------------------------------------------- reporting ---
def fmt(out):
    L = []
    P = L.append
    tot_reads = out["reads_total"]
    P("=" * 78)
    P("CHOICE CENSUS -- all real FF9 fields (F3 dialogue-lockstep, CHOICES lane)")
    P("=" * 78)
    P(f"fields scanned .............................. {out['n_fields']}")
    P(f"fields with >=1 GetChoose read .............. {out['fields_with_choice']} "
      f"({100*out['fields_with_choice']/out['n_fields']:.0f}%)")
    P(f"total GetChoose (B_SYSVAR[9]) reads ......... {tot_reads}")
    P(f"functions containing a choice read .......... {out['funcs_with_choice']}")
    P(f"EnableDialogChoices (0x7C) setup ops ........ {out['enable_total']}")
    P("")
    P("--- Q1  read host opcode (where the GetChoose token sits) ---")
    for op, n in out["read_host_op"].most_common():
        P(f"    {op:<20} {n}")
    P("")
    P("--- Q1/Q3  consumption class per read ---")
    for c in ("SWITCH", "IF", "STORE", "OTHER"):
        n = out["read_class"][c]
        P(f"    {c:<8} {n:>5}  ({100*n/tot_reads:.1f}%)")
    P(f"    IF compare ops: {dict(out['if_cmp'].most_common())}")
    P(f"    STORE target scope: {dict(out['store_scope'].most_common())}")
    P("")
    P("--- Q2  dispatch SITES + row counts ---")
    P(f"    switch-dispatch sites ....... {out['switch_sites']}")
    P(f"      rows -> #sites: {dict(sorted(out['switch_rows'].items()))}")
    P(f"    if-chain sites (grouped) .... {out['ifchain_sites']}")
    P(f"      rows -> #sites: {dict(sorted(out['ifchain_rows'].items()))}")
    P(f"    total branch sites .......... {out['switch_sites'] + out['ifchain_sites']}")
    P(f"    EnableDialogChoices default row dist: {dict(sorted(out['enable_default'].items()))}")
    P(f"    0x7C mask with bit15 set (sign-extend risk): {out['enable_mask_bit15']}")
    P(f"    0x7C default >= 16: {out['enable_default_ge_16']}")
    P("")
    P("--- Q2  softlock family: Menu(0x75) opcode arg0 (id 4 = party-change) ---")
    P(f"    Menu arg0 dist: {dict(sorted(out['menu_arg0'].items()))}")
    P(f"    fields opening Menu(4,*) party-change: {len(out['menu_party_fields'])}")
    P(f"    big dialog menus (>=10 rows) examples: {out['big_menu_examples'][:12]}")
    P("")
    P("--- Q3/Q5  consequence bucket per BRANCH site (arms delimited from the .eb) ---")
    tot_sites = sum(out["site_class"].values())
    for c in ("GLOB_only", "WARP", "ITEM_MENU", "INERT", "DIV_GLOB", "DIV_ONLY"):
        n = out["site_class"][c]
        P(f"    {c:<10} {n:>5}  ({100*n/tot_sites:.1f}%)")
    P(f"    (by kind) switch : {dict(out['site_class_by_kind']['switch'])}")
    P(f"    (by kind) ifchain: {dict(out['site_class_by_kind']['ifchain'])}")
    P(f"    OVERLAPPING arm attributes (a site may have several): {dict(out['site_attr'].most_common())}")
    P("")
    P("--- Q3/Q5  consequence bucket per STORE read (target scope) ---")
    tot_store = sum(out["store_class"].values())
    for c in ("GLOB_only", "DIVERGENT"):
        n = out["store_class"][c]
        pct = (100 * n / tot_store) if tot_store else 0
        P(f"    {c:<10} {n:>5}  ({pct:.1f}%)")
    P("")
    P("--- Q4  nesting / chaining / ATE ---")
    P(f"    functions with >1 branch site (sequence) ... {out['funcs_multi_site']}")
    P(f"    branch sites whose arms contain a choice ... {out['nested_sites']}")
    P(f"    choice functions co-located with AICON(ATE)  {out['ate_choice_funcs']}")
    P("")
    P("--- Q5  F3 headline: cosmetically-free vs must-force ---")
    free = out["site_class"]["GLOB_only"] + out["site_class"]["WARP"] + \
        out["site_class"]["ITEM_MENU"] + out["site_class"]["INERT"]
    div_glob = out["site_class"]["DIV_GLOB"]
    div_only = out["site_class"]["DIV_ONLY"]
    P(f"    story-safe (GLOB mirrors / WARP follows / ITEM local / INERT): "
      f"{free} ({100*free/tot_sites:.1f}%)")
    P(f"    DIV_GLOB (transient presentation differs, but a GLOB flag in the arm still mirrors the story): "
      f"{div_glob} ({100*div_glob/tot_sites:.1f}%)")
    P(f"    DIV_ONLY (transient MAP/INST only, NO glob -- per-visit divergence, wiped on field reload): "
      f"{div_only} ({100*div_only/tot_sites:.1f}%)")
    P(f"    => story state is NEVER permanently divergent (all GLOB writes mirror); the F3 cost of a free "
      f"guest pick is per-visit VISIBLE branch divergence on {div_glob + div_only} sites")
    store_div = out["store_class"]["DIVERGENT"]
    store_free = out["store_class"]["GLOB_only"]
    P(f"    STORE reads: GLOB(mirrored)={store_free}  MAP/INST(divergent)={store_div}")
    P("")
    P("--- Q5  field-level F3 scoping ---")
    P(f"    fields with choices ......................... {out['fields_with_choice']}")
    P(f"    fields where EVERY choice is story-safe ..... {out['fields_all_safe']} "
      f"(guest picks entirely free)")
    P(f"    fields with >=1 purely-transient (DIV_ONLY/INST-store) choice: {len(out['fields_div_only'])} "
      f"(the F3 special-handling set)")
    P(f"    >=10-row switch menus by func tag: {dict(out['big_menu_tag'].most_common())}")
    P("=" * 78)
    top = out["per_field_reads"].most_common(12)
    P(f"top fields by #reads: {top}")
    return "\n".join(L)


if __name__ == "__main__":
    data = census()
    report = fmt(data)
    print(report)
    if "--dump-tables" in sys.argv:
        (Path(__file__).parent / "choices_census_output.txt").write_text(report + "\n", encoding="utf-8")
