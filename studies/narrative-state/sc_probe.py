"""Recon probe: how well can a 'SC window' be derived per story bit from the real corpus?

For every real field .eb:
  - count SC (Global.UInt16[0]) absolute writes, compound writes, and comparison GATES
  - count switch statements (0x06/0x0B/0x0D) whose selector expression reads Global.UInt16[0]
  - for every GLOB Bit write, record the NEAREST PRECEDING SC comparison constant in the SAME function
    (crude proxy for 'the SC window in which this bit is written')
Prints aggregate feasibility numbers. No files written.
"""
import os, sys, json, struct
from collections import defaultdict

_HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(_HERE))  # studies/narrative-state/ -> repo root
for p in (os.path.join(REPO, "ff9mapkit"), REPO):
    if p not in sys.path:
        sys.path.insert(0, p)

from ff9mapkit.extract import EventBundle, ID_TO_EVT   # noqa: E402
from ff9mapkit.eb import EbScript                      # noqa: E402
from ff9mapkit.eb.disasm import decode_switch          # noqa: E402

T_CONST16, T_END = 0x7D, 0x7F
CMP_OPS = {24: "<", 25: ">", 26: "<=", 27: ">=", 28: "<", 29: ">", 30: "<=", 31: ">=",
           32: "==", 33: "!=", 34: "==", 35: "!="}
PURE_ASSIGN = {0x2C, 0x2D, 0x2E}
ASSIGN_ALL = set(range(0x2C, 0x46)) | set(range(0x04, 0x0C))


def glob_var(d, off):
    """(vartype, index, len) if d[off] is a GLOBAL var token, else None."""
    if off >= len(d):
        return None
    b = d[off]
    if b < 0xC0:
        return None
    if (b & 3) != 0:                    # source must be Global
        return None
    long_idx = bool(b & 0x20)
    vt = (b >> 2) & 7
    if long_idx:
        if off + 2 >= len(d):
            return None
        return (vt, d[off + 1] | (d[off + 2] << 8), 3)
    if off + 1 >= len(d):
        return None
    return (vt, d[off + 1], 2)


def main():
    bundle = EventBundle()
    ids = sorted(ID_TO_EVT.keys())
    sc_abs_writes = 0
    sc_rel_writes = 0
    sc_gates = 0
    sc_gate_ops = defaultdict(int)
    sc_switch_fields = set()
    sc_switch_maininit = set()
    sc_switch_cases = []
    fields_with_sc_gate = set()
    bit_writes = 0
    bit_writes_windowed = 0
    bits_all = set()
    bits_windowed = set()
    bit_window = defaultdict(set)       # bit -> {(op, const)}
    bit_writers = defaultdict(set)
    bit_clear_sites = 0
    bits_ever_cleared, bits_ever_set = set(), set()
    scanned = 0
    for fid in ids:
        try:
            data = bundle.eb_for_id(fid)
            if not data:
                continue
            eb = EbScript.from_bytes(data)
        except Exception:
            continue
        scanned += 1
        d = eb.data
        for ei, e in enumerate(eb.entries):
            if e.empty:
                continue
            for fi, f in enumerate(e.funcs):
                last_sc = None          # (op, const) most recent SC comparison in this function
                last_stmt_sc_read = False   # previous 0x05 was a bare read of Global.UInt16[0]
                for ins in eb.instrs(f):
                    if ins.op in (0x06, 0x0B, 0x0D):
                        si = decode_switch(ins)
                        if last_stmt_sc_read:
                            sc_switch_fields.add(fid)
                            if ei == 0 and fi == 0:
                                sc_switch_maininit.add(fid)
                            if si is not None:
                                try:
                                    sc_switch_cases.append(len(si.cases))
                                except Exception:
                                    pass
                        continue
                    if ins.op != 0x05:
                        continue
                    gv = glob_var(d, ins.off + 1)
                    if gv is None:
                        last_stmt_sc_read = False
                        continue
                    vt, idx, vlen = gv
                    p = ins.off + 1 + vlen
                    # walk the statement tokens to the first END
                    val = None
                    op = None
                    q = p
                    while q < ins.end and q < len(d):
                        bb = d[q]
                        if bb == T_CONST16 and q + 2 < len(d):
                            val = struct.unpack("<h", d[q + 1:q + 3])[0]
                            q += 3
                            continue
                        if bb == T_END:
                            break
                        if bb in ASSIGN_ALL or bb in CMP_OPS:
                            op = bb
                            break
                        q += 1
                    last_stmt_sc_read = (vt in (6, 7) and idx == 0 and op is None)
                    if vt in (6, 7) and idx == 0:            # ScenarioCounter
                        if op in PURE_ASSIGN:
                            sc_abs_writes += 1
                        elif op in ASSIGN_ALL:
                            sc_rel_writes += 1
                        elif op in CMP_OPS and val is not None:
                            sc_gates += 1
                            sc_gate_ops[CMP_OPS[op]] += 1
                            fields_with_sc_gate.add(fid)
                            last_sc = (CMP_OPS[op], val)
                    elif vt in (0, 1) and op in ASSIGN_ALL:  # a GLOB bit WRITE
                        bit_writes += 1
                        bits_all.add(idx)
                        bit_writers[idx].add(fid)
                        if op in PURE_ASSIGN and val == 0:
                            bit_clear_sites += 1
                            bits_ever_cleared.add(idx)
                        elif op in PURE_ASSIGN and val == 1:
                            bits_ever_set.add(idx)
                        if last_sc is not None:
                            bit_writes_windowed += 1
                            bits_windowed.add(idx)
                            bit_window[idx].add(last_sc)
    print(json.dumps({
        "fields_scanned": scanned,
        "sc_absolute_writes": sc_abs_writes,
        "sc_relative_writes": sc_rel_writes,
        "sc_comparison_gates": sc_gates,
        "sc_gate_ops": dict(sc_gate_ops),
        "fields_with_any_sc_gate": len(fields_with_sc_gate),
        "fields_with_sc_switch": len(sc_switch_fields),
        "fields_with_sc_switch_in_main_init": len(sc_switch_maininit),
        "sc_switch_case_counts_total": len(sc_switch_cases),
        "glob_bit_write_sites": bit_writes,
        "glob_bit_write_sites_with_preceding_sc_cmp_in_func": bit_writes_windowed,
        "distinct_bits_written": len(bits_all),
        "distinct_bits_with_at_least_one_sc_window": len(bits_windowed),
        "bits_with_exactly_one_sc_window": sum(1 for b, s in bit_window.items() if len(s) == 1),
        "bits_single_writer_field": sum(1 for b, s in bit_writers.items() if len(s) == 1),
        "bit_clear_to_zero_sites": bit_clear_sites,
        "bits_ever_cleared": len(bits_ever_cleared),
        "bits_ever_set_to_one": len(bits_ever_set),
        "bits_both_set_and_cleared": len(bits_ever_cleared & bits_ever_set),
    }, indent=2))
    dump = {str(b): {"writers": sorted(bit_writers[b]),
                     "set1": b in bits_ever_set, "clear0": b in bits_ever_cleared,
                     "windows": sorted(list(x) for x in bit_window.get(b, ()))}
            for b in sorted(bits_all)}
    json.dump(dump, open(os.path.join(_HERE, "bit_dump.json"), "w"), indent=1)
    print("wrote bit_dump.json", len(dump))


main()
