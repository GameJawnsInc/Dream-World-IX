"""Empirical census of FF9 story-flag (gEventGlobal) usage across every real field.

Story-flag research (story_flags branch). Reads each real field's compiled `.eb` straight from the
game install's p0data (via the kit's EventBundle), walks every expression statement (opcode 0x05),
and decodes the GLOBAL-source variable it touches -- byte-exact against the engine's own decoder
(EBin.getVarOperation / GetVariableValueInternal):

    var byte = 0xC0 | (VariableType << 2) | VariableSource     (+ 0x20 = long 2-byte index)
      VariableSource: 0=Global(save-persistent gEventGlobal) 1=Map(transient) 2=Instance 3=Null
      VariableType:   0=SBit 1=Bit 2=Int24 3=UInt24 4=SByte 5=Byte 6=Int16 7=UInt16
      addressing:     Bit/SBit -> ofs is a BIT index (byte=ofs>>3, bit=ofs&7); all others -> BYTE index

We keep ONLY VariableSource.Global (the save-backed 2048-byte gEventGlobal == the story-flag heap).
Map/Instance vars are session-transient and never cross-field story state.

Output: research/flag_census.json  (per-index aggregation, per-field summary, scenario-counter map,
overall stats) + a printed human summary.

Run from the kit root so the local package shadows any editable install:
    cd ff9mapkit && py ../research/flag_census.py
"""
from __future__ import annotations
import sys, os, json, struct
from collections import defaultdict

# Make the kit importable whether run from repo root or kit root.
_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
for p in (os.path.join(_REPO, "ff9mapkit"), _REPO):
    if p not in sys.path:
        sys.path.insert(0, p)

from ff9mapkit.extract import EventBundle, ID_TO_EVT, ID_TO_FBG          # noqa: E402
from ff9mapkit.eb import EbScript                                         # noqa: E402

VARTYPE = {0: "SBit", 1: "Bit", 2: "Int24", 3: "UInt24", 4: "SByte", 5: "Byte", 6: "Int16", 7: "UInt16"}
SRC_GLOBAL = 0

# expression operator tokens (EBin.op_binary, EBin.cs:2423-2485) — the operators that WRITE their LHS.
# The full assignment family is B_LET(44=0x2C) .. B_OR_LET_E(69=0x45): plain `=` (0x2C/0x2D/0x2E _A/_E
# variants) + every compound-assign (`*= /= %= += -= <<= >>= &= ^= |=` and their _A/_E forms). Plus the
# in/decrement ops B_POST_PLUS(4) .. B_PRE_MINUS_A(11) which mutate the var with no const operand.
T_CONST16 = 0x7D
T_END = 0x7F
_ASSIGN_NAME = {
    0x2C: "=", 0x2D: "=", 0x2E: "=", 0x2F: "*=", 0x30: "/=", 0x31: "%=", 0x32: "+=", 0x33: "-=",
    0x34: "<<=", 0x35: ">>=", 0x36: "*=", 0x37: "/=", 0x38: "%=", 0x39: "+=", 0x3A: "-=",
    0x3B: "<<=", 0x3C: ">>=", 0x3D: "&=", 0x3E: "^=", 0x3F: "|=", 0x40: "&=", 0x41: "^=",
    0x42: "|=", 0x43: "&=", 0x44: "^=", 0x45: "|=",
    0x04: "++", 0x05: "--", 0x06: "++", 0x07: "--", 0x08: "++", 0x09: "--", 0x0A: "++", 0x0B: "--",
}
ASSIGN_OPS = _ASSIGN_NAME                       # any of these after the var => the var is WRITTEN
PURE_ASSIGN = {0x2C, 0x2D, 0x2E}                # B_LET/_A/_E -> an ABSOLUTE set (records a milestone value)
JMP_FALSE, JMP_TRUE = 0x02, 0x03


def decode_global_var(data: bytes, off: int):
    """If data[off] is a GLOBAL-source var token, return (vartype:int, index:int, token_len:int); else None."""
    if off >= len(data):
        return None
    b = data[off]
    if (b & 0xC0) != 0xC0:                 # not a var token
        return None
    src = b & 0x03
    if src != SRC_GLOBAL:                  # keep only save-persistent gEventGlobal
        return None
    vtype = (b >> 2) & 0x07
    is_long = bool(b & 0x20)
    if is_long:
        if off + 2 >= len(data):
            return None
        idx = data[off + 1] | (data[off + 2] << 8)
        return (vtype, idx, 3)
    if off + 1 >= len(data):
        return None
    return (vtype, data[off + 1], 2)


def statement_tokens(data: bytes, start: int, limit: int = 64):
    """Bytes of the 0x05 expression statement beginning at `start` (the var token), up to the first
    top-level 0x7F (END), capped at `limit`. Returns (stmt_bytes, end_off)."""
    p = start
    end = min(len(data), start + limit)
    while p < end:
        if data[p] == T_END:
            return data[start:p + 1], p
        p += 1
    return data[start:end], end


def classify(data: bytes, var_off: int, var_len: int):
    """Classify the role of the GLOBAL var at var_off within its 0x05 statement.
    Returns (role, value, op_byte) where role in {'write','gate','read'}, value = the i16 constant
    assigned (for writes, or None for an in/decrement), and op_byte = the raw assignment opcode (or
    None). 'gate' = a read that drives a conditional jump (if/ifnot)."""
    stmt, end = statement_tokens(data, var_off)
    # the var is the first token; what follows decides the role
    after = var_off + var_len
    # WRITE: an assignment op appears before END (`7D <i16> <op> 7F` for set/compound, or `<op> 7F`
    # for an in/decrement). The var is the RPN LHS, so the first assign op binds to it.
    op_seen = None
    val = None
    q = after
    while q < end:
        bb = data[q]
        if bb == T_CONST16 and q + 2 < len(data):
            val = struct.unpack("<h", data[q + 1:q + 3])[0]
            q += 3
            continue
        if bb in ASSIGN_OPS:
            op_seen = bb
            break
        if bb == T_END:
            break
        q += 1
    if op_seen is not None:
        return ("write", val, op_seen)
    # READ: is it a gate? END followed by a conditional jump (covers the negated `0E 7F` form too,
    # since statement_tokens returns at the first 7F).
    if end + 1 < len(data) and data[end] == T_END and data[end + 1] in (JMP_FALSE, JMP_TRUE):
        return ("gate", None, None)
    return ("read", None, None)


def expr_var_offsets(eb: EbScript):
    """Yield (off) of the byte AFTER each 0x05 EXPR opcode (== the var token position)."""
    d = eb.data
    for e in eb.entries:
        if e.empty:
            continue
        for f in e.funcs:
            for ins in eb.instrs(f):
                if ins.op == 0x05:
                    yield ins.off + 1


def main():
    print("loading field event bundle from p0data ...", flush=True)
    bundle = EventBundle()
    ids = sorted(ID_TO_EVT.keys())
    print(f"  {len(ids)} mapped field ids\n", flush=True)

    # aggregations
    bit_writers = defaultdict(set)      # bit_index -> {field_id}
    bit_readers = defaultdict(set)      # bit_index -> {field_id} (gate or read)
    bit_gaters = defaultdict(set)
    word_use = defaultdict(set)         # (vartype, byte_idx) -> {field_id}
    scenario_writes = defaultdict(set)  # ABSOLUTE value -> {field_id} (Global 16-bit `=` at byte 0)
    scenario_increments = defaultdict(set)  # op-name ('+=','-=',..) -> {field_id} (relative scenario change)
    per_field = {}                      # field_id -> {bits_set, bits_read, words, scenario_sets}
    scanned = 0
    errors = []

    for fid in ids:
        try:
            eb_bytes = bundle.eb_for_id(fid)
        except Exception as ex:                      # noqa: BLE001
            errors.append((fid, repr(ex)))
            continue
        if not eb_bytes:
            continue
        try:
            eb = EbScript.from_bytes(eb_bytes)
        except Exception as ex:                      # noqa: BLE001
            errors.append((fid, repr(ex)))
            continue
        scanned += 1
        d = eb.data
        f_bits_w, f_bits_r, f_words, f_scn, f_scn_inc = set(), set(), set(), [], []
        for off in expr_var_offsets(eb):
            dec = decode_global_var(d, off)
            if dec is None:
                continue
            vtype, idx, vlen = dec
            role, val, op = classify(d, off, vlen)
            if vtype in (0, 1):              # Bit / SBit -> bit-flag
                if role == "write":
                    bit_writers[idx].add(fid); f_bits_w.add(idx)
                elif role == "gate":
                    bit_gaters[idx].add(fid); bit_readers[idx].add(fid); f_bits_r.add(idx)
                else:
                    bit_readers[idx].add(fid); f_bits_r.add(idx)
            else:                            # multi-byte word (Byte/Int16/UInt16/Int24...)
                word_use[(vtype, idx)].add(fid); f_words.add((vtype, idx))
                if idx == 0 and vtype in (6, 7) and role == "write":
                    if op in PURE_ASSIGN and val is not None:       # absolute milestone set
                        scenario_writes[val].add(fid); f_scn.append(val)
                    elif op is not None:                            # relative change (+=/-=/++/--)
                        nm = _ASSIGN_NAME.get(op, hex(op))
                        scenario_increments[nm].add(fid); f_scn_inc.append(nm)
        per_field[fid] = {
            "evt": ID_TO_EVT.get(fid), "fbg": ID_TO_FBG.get(fid),
            "bits_set": sorted(f_bits_w), "bits_read": sorted(f_bits_r),
            "words": sorted([list(w) for w in f_words]),
            "scenario_sets": sorted(set(f_scn)),
            "scenario_increments": sorted(set(f_scn_inc)),
        }

    # ---- assemble report ----
    all_bits = sorted(set(bit_writers) | set(bit_readers))
    bit_index = {}
    for b in all_bits:
        bit_index[b] = {
            "byte": b >> 3, "bit": b & 7,
            "writers": sorted(bit_writers.get(b, ())),
            "readers": sorted(bit_readers.get(b, ())),
            "gaters": sorted(bit_gaters.get(b, ())),
            "n_write": len(bit_writers.get(b, ())), "n_read": len(bit_readers.get(b, ())),
        }
    words = {f"{VARTYPE[t]}@byte{ix}": sorted(fs) for (t, ix), fs in sorted(word_use.items())}
    scenario = {str(v): sorted(fs) for v, fs in sorted(scenario_writes.items())}
    scenario_inc = {nm: sorted(fs) for nm, fs in sorted(scenario_increments.items())}

    report = {
        "summary": {
            "fields_scanned": scanned, "fields_mapped": len(ids),
            "distinct_bit_flags": len(all_bits),
            "bit_flag_min": all_bits[0] if all_bits else None,
            "bit_flag_max": all_bits[-1] if all_bits else None,
            "distinct_word_vars": len(word_use),
            "distinct_scenario_values": len(scenario_writes),
            "scenario_increment_ops": {nm: len(fs) for nm, fs in scenario_inc.items()},
            "scan_errors": len(errors),
        },
        "bit_flags": bit_index,
        "word_vars": words,
        "scenario_counter_writes": scenario,
        "scenario_counter_increments": scenario_inc,
        "per_field": per_field,
        "errors": errors[:50],
    }
    out = os.path.join(_HERE, "flag_census.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1)

    s = report["summary"]
    print("=== FF9 gEventGlobal usage census ===")
    print(f"  fields scanned (with .eb): {s['fields_scanned']} / {s['fields_mapped']} mapped")
    print(f"  distinct bit-flags used:   {s['distinct_bit_flags']}  (bit range {s['bit_flag_min']}..{s['bit_flag_max']})")
    print(f"  distinct word vars used:   {s['distinct_word_vars']}  (Byte/Int16/UInt16 at fixed byte offsets)")
    print(f"  distinct scenario values:  {s['distinct_scenario_values']}  (Global 16-bit writes at byte 0)")
    print(f"  scan errors:               {s['scan_errors']}")
    # histogram of bit-flag usage by byte
    bybyte = defaultdict(int)
    for b in all_bits:
        bybyte[b >> 3] += 1
    print(f"\n  bit-flags span {len(bybyte)} distinct bytes of the 2048-byte heap")
    print(f"  busiest bytes (byte: #distinct bits): " +
          ", ".join(f"{by}:{n}" for by, n in sorted(bybyte.items(), key=lambda kv: -kv[1])[:12]))
    # hottest flags
    hot = sorted(all_bits, key=lambda b: -(len(bit_writers.get(b, ())) + len(bit_readers.get(b, ()))))[:15]
    print("\n  hottest flags (bit idx -> #writers/#readers):")
    for b in hot:
        print(f"    bit {b:5d} (byte {b>>3}.{b&7}): {len(bit_writers.get(b,())):3d}w {len(bit_readers.get(b,())):3d}r")
    print(f"\n  wrote {out}")


if __name__ == "__main__":
    main()
