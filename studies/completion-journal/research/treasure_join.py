"""treasure_join.py -- section 7.2 Q2: the grant<->latch join residue, MEASURED.

The question this answers: for how many of the game's literal item/gil grants can the
once-latch GLOB bit be derived UNAMBIGUOUSLY by machine? That single number decides
whether the T4 chest atlas is a generator project (high) or a hand-mining program (low).

For every literal AddItem/AddGil in every real field's event script, join the grant to
its latch using the kill-aware CFG (``ff9mapkit.eb.cfg``):

  guard side : dominator-chain guards testing ``Global.Bit[N] == 0`` -- taken RAW
               (un-killed) on purpose: in the classic idiom
               ``if (bit==0) { bit=1; AddItem }`` the latch write kills its own guard
               at the grant site, which is exactly the pairing we are looking for
  write side : ``Global.Bit[N] = 1`` assignments inside the grant's innermost guarded
               region (weaker fallback: anywhere in the same function)

Per-grant classes:
  latch        exactly one bit on BOTH sides            -- generator-grade
  latch-write  exactly one write-side bit, no guard-side -- strong (arm/caller-guarded)
  latch-guard  exactly one guard-side bit, no write-side -- weak (latched elsewhere)
  ambiguous    >1 candidate on the deciding side
  sc-window    no latch, but a ScenarioCounter guard     -- cutscene reward, windowed
  bare         no latch, no SC                           -- repeatable (shop/visit grants)
  unresolved   computed item operand                     -- the fidelity ceiling

Output: the global residue, the 20 grant-densest fields as the Q2 slice, and
``treasure_join.json`` next to this file (gitignored -- derived from the user's own
install, regenerable).

Run from ``ff9mapkit/`` (so the local package shadows any editable install):

    py ../studies/completion-journal/research/treasure_join.py
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

from ff9mapkit.extract import EventBundle, ID_TO_EVT            # noqa: E402
from ff9mapkit.eb import EbScript                               # noqa: E402
from ff9mapkit.eb.cfg import FieldFlow                          # noqa: E402
from ff9mapkit import forkreport as FR                          # noqa: E402

ADD_ITEM_OP = 0x48
ADD_GIL_OP = 0xCE

# Treasure-Hunter scoring, verified against EventState.cs:65-70 THIS pass:
# bytes 896-960 and 966-975 at 1 pt/bit, bytes 182-186 at 2 pts/bit (the chocograph band --
# a detail PLAN.md's blocker list does not carry).
_TH_SINGLE = set(range(896 * 8, 961 * 8)) | set(range(966 * 8, 976 * 8))
_TH_DOUBLE = set(range(182 * 8, 187 * 8))


def _imm(ins, i):
    """Literal operand i of a disasm Instr, or None when it is an expression."""
    if i >= len(ins.args) or (ins.arg_is_expr and ins.arg_is_expr[i]):
        return None
    v = ins.args[i]
    return int(v) if isinstance(v, int) else None


def _load_names() -> dict[int, str]:
    """field id -> room name from reference/field-manifest.tsv (index != field id)."""
    names: dict[int, str] = {}
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


def main() -> int:
    bundle = EventBundle()
    names = _load_names()
    grants: list[dict] = []
    stats: Counter = Counter()
    per_field: Counter = Counter()

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

        for key, fl in ff.flows.items():
            ei, fi = key
            ftag = eb.entries[ei].funcs[fi].tag
            ctx = ff.ctx.get(key, {})
            ctx_unset_bits = {c.index for c in ctx
                              if c.is_glob_bit and c.cmp == "==" and c.value == 0}
            ctx_sc = any(c.is_scenario for c in ctx)

            # write side, precomputed per function: every literal Bit[N] = 1
            bit_sets = [(st, blk) for st, blk in fl.iter_sets(eb.data)
                        if st.kind == "assign" and st.source == 0
                        and st.vtype in (0, 1) and st.value == 1]

            for blk in fl.blocks:
                if fl._dom[blk.index] == 0:
                    continue                                    # dead code claims nothing
                for ins in blk.instrs:
                    if ins.op == ADD_ITEM_OP:
                        iid = _imm(ins, 0)
                        if iid is None:
                            stats["unresolved"] += 1
                            per_field[fid] += 1
                            grants.append({"field": fid, "entry": ei, "func": ftag,
                                           "off": ins.off, "kind": "item", "id": None,
                                           "cls": "unresolved"})
                            continue
                        if iid == FR.NO_ITEM or FR.item_inert(iid):
                            continue                            # engine no-op, not a grant
                        g = {"kind": "item", "id": iid, "count": _imm(ins, 1),
                             "label": FR.item_label(iid)}
                    elif ins.op == ADD_GIL_OP:
                        amt = _imm(ins, 0)
                        g = {"kind": "gil", "id": None, "amount": amt}
                    else:
                        continue

                    b = blk.index
                    root = fl.innermost_guard_block(b)
                    region = set(fl.dominated_by(root)) if root is not None else {b}

                    # guard side: RAW dominator-chain guards (un-killed, see module doc)
                    guard_bits = set(ctx_unset_bits)
                    for _d, conds in fl._raw_guards(b):
                        for c in conds:
                            if c.is_glob_bit and c.cmp == "==" and c.value == 0:
                                guard_bits.add(c.index)
                    # write side: latch writes inside the innermost guarded region
                    region_writes = {st.index for st, wb in bit_sets if wb in region}
                    func_writes = {st.index for st, _wb in bit_sets}

                    both = guard_bits & region_writes
                    if len(both) == 1:
                        cls, latch = "latch", next(iter(both))
                    elif len(both) > 1:
                        cls, latch = "ambiguous", sorted(both)
                    elif len(region_writes) == 1:
                        cls, latch = "latch-write", next(iter(region_writes))
                    elif len(region_writes) > 1:
                        cls, latch = "ambiguous", sorted(region_writes)
                    elif len(guard_bits) == 1:
                        gb = next(iter(guard_bits))
                        # a guard-side-only bit that the function ALSO never latches is
                        # only trustworthy if somebody writes it; keep the class honest
                        cls, latch = ("latch-guard", gb) if gb not in func_writes \
                            else ("latch", gb)
                    elif len(guard_bits) > 1:
                        cls, latch = "ambiguous", sorted(guard_bits)
                    else:
                        r = fl.guards_at_ex(ins.off)
                        live = list(r[0]) if r else []
                        if ctx_sc or any(c.is_scenario for c in live):
                            cls, latch = "sc-window", None
                        else:
                            cls, latch = "bare", None

                    stats[cls] += 1
                    per_field[fid] += 1
                    g.update({"field": fid, "entry": ei, "func": ftag, "off": ins.off,
                              "cls": cls, "latch": latch})
                    if isinstance(latch, int):
                        g["th"] = (2 if latch in _TH_DOUBLE
                                   else 1 if latch in _TH_SINGLE else 0)
                    grants.append(g)

    total = sum(stats[k] for k in
                ("latch", "latch-write", "latch-guard", "ambiguous",
                 "sc-window", "bare", "unresolved"))
    strong = stats["latch"] + stats["latch-write"]
    single = strong + stats["latch-guard"]
    th_item_latches = sorted({g["latch"] for g in grants
                              if g["kind"] == "item" and g.get("th") and
                              isinstance(g.get("latch"), int)})

    out = {
        "generator": "studies/completion-journal/research/treasure_join.py",
        "engine_truth": {
            "th_bytes_1pt": "896-960, 966-975",
            "th_bytes_2pt": "182-186 (EventState.cs:69-70 -- absent from PLAN.md)",
        },
        "stats": dict(sorted(stats.items())),
        "summary": {
            "grant_sites_total": total,
            "strong_single_latch": strong,
            "any_single_latch": single,
            "any_single_latch_pct": round(single / total * 100, 1) if total else 0.0,
            "ambiguous": stats["ambiguous"],
            "sc_window": stats["sc-window"],
            "bare": stats["bare"],
            "unresolved": stats["unresolved"],
            "distinct_th_scored_item_latches": len(th_item_latches),
        },
        "top20_fields": [
            {"field": fid, "name": names.get(fid, "?"), "grants": n,
             "classes": dict(Counter(g["cls"] for g in grants if g["field"] == fid))}
            for fid, n in per_field.most_common(20)
        ],
        "grants": grants,
    }
    dest = os.path.join(_HERE, "treasure_join.json")
    with open(dest, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)

    print(json.dumps({"stats": out["stats"], "summary": out["summary"],
                      "top20_fields": out["top20_fields"]}, indent=2))
    print(f"wrote {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
