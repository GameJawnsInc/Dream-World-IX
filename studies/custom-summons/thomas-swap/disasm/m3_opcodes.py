"""m3_opcodes -- regenerate the 216-entry native-call (HLE syscall) opcode table.

Slice M3 of the summon-cutscene disasm round. Reads the user's OWN installed
FF9SpecialEffectPlugin.dll (x64 + x86) and emits RVAs/indices only -- zero game bytes.

The dispatcher is fn 0xee80 (x64): `int nativeCall(PsxCtx* ctx, int opcode)` with
`cmp edx,0xd7; ja default` @0xee98 => 216 opcodes. Two independent, opcode-indexed
tables exist and agree:
    .text 0x12358  216 x u32  image-relative jump-table target per opcode
    .data 0x68780  216 x u64  primary native function per opcode (x64)
    x86  0x50e18   216 x u32  the same table in the 32-bit build

Usage:
    py m3_opcodes.py            # print the table
    py m3_opcodes.py --json out.json
    py m3_opcodes.py --check    # assert the load-bearing invariants
"""
from __future__ import annotations
import argparse
import json
import struct

import refkit

N_OPS = 216
JT_X64 = 0x12358          # .text, image-relative dword offsets
FT_X64 = 0x68780          # .data, absolute qword fn pointers
FT_X86 = 0x50e18          # .data, absolute dword fn pointers
DISPATCH_X64 = 0xee80     # real entry (0xeea4 is the post-bound-check continuation)
GET_ARG_INT = 0x126c0
GET_ARG_PTR = 0x12740
PSX_PTR = 0x10e0

# opcode -> name, established by BOTH tables agreeing plus the leftover debug strings
SUMMON_OPS = {
    11: "Hi_StopSummonTexAnim",
    12: "Hi_StartSummonTexAnim",
    23: "Hi_RegisterSummonModel",
    25: "Hi_DrawSummonModel",
    26: "Hi_SetSummonMotion",
    65: "Hi_ModifySummonModelRGB",
    100: "Hi_SetSummonMotFrame",
    147: "Hi_ModifySummonModelAbr",
    149: "Hi_GetSummonBonePos",
    157: "Hi_ShowSummonModelMesh",
    158: "Hi_HideSummonModelMesh",
    164: "Hi_GetSummonBoneMatrix",
}


def tables():
    """(jump_table_x64, fn_table_x64, fn_table_x86) -- all RVA lists of length 216."""
    pe = refkit.load()
    base = refkit.image_base(pe)
    jt = list(struct.unpack("<%dI" % N_OPS, refkit.read_rva(pe, JT_X64, N_OPS * 4)))
    ft = [(v - base) if v else 0
          for v in struct.unpack("<%dQ" % N_OPS, refkit.read_rva(pe, FT_X64, N_OPS * 8))]
    pe86 = refkit.load("x86")
    b86 = refkit.image_base(pe86)
    ft86 = [(v - b86) if v else 0
            for v in struct.unpack("<%dI" % N_OPS, refkit.read_rva(pe86, FT_X86, N_OPS * 4))]
    return jt, ft, ft86


def x86_arity(pe86, rva: int):
    """Arity from the x86 cdecl frame: max [ebp+N] -> (N-8)/4 + 1. None if no ebp frame."""
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    import re
    if not rva:
        return None
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    base = refkit.image_base(pe86)
    rx = re.compile(r"ebp \+ (0x[0-9a-f]+|\d+)\]")
    mx, seen, frame = 0, False, False
    for i, ins in enumerate(md.disasm(refkit.read_rva(pe86, rva, 0x1200), base + rva)):
        if i <= 2 and ins.mnemonic == "mov" and ins.op_str == "ebp, esp":
            frame = True
        for m in rx.finditer(ins.op_str):
            v = int(m.group(1), 0)
            if v >= 8:
                mx, seen = max(mx, v), True
        if ins.mnemonic == "ret" or i > 1500:
            break
    if not frame:
        return None
    return ((mx - 8) // 4 + 1) if seen else 0


def build():
    jt, ft, ft86 = tables()
    pe86 = refkit.load("x86")
    rows = []
    for op in range(N_OPS):
        rows.append({
            "op": op,
            "handler_x64": jt[op],
            "fn_x64": ft[op],
            "fn_x86": ft86[op],
            "arity": x86_arity(pe86, ft86[op]),
            "name": SUMMON_OPS.get(op),
        })
    return rows


def check():
    jt, ft, ft86 = tables()
    pe = refkit.load()
    bad = []
    for op, want in ((157, 0x187e0), (158, 0x18840), (23, 0x15ee0), (25, 0x17710),
                     (26, 0x17a10), (100, 0x17a70), (164, 0x18630), (149, 0x185b0)):
        if ft[op] != want:
            bad.append("x64 op %d -> 0x%05x, expected 0x%05x" % (op, ft[op], want))
    for op, want in ((157, 0x14730), (158, 0x14780), (23, 0x13080), (25, 0x13ce0), (26, 0x13f40)):
        if ft86[op] != want:
            bad.append("x86 op %d -> 0x%05x, expected 0x%05x" % (op, ft86[op], want))
    if ft[20] or ft86[20]:
        bad.append("op 20 should be NULL in both builds")
    if refkit.read_rva(pe, JT_X64 + N_OPS * 4, 1) != b"\xcc":
        bad.append("jump table does not end at 216 entries (no 0xCC padding at 0x126b8)")
    if not all(DISPATCH_X64 <= t < JT_X64 for t in jt):
        bad.append("a jump-table target falls outside the dispatcher body")
    print("FAIL:\n  " + "\n  ".join(bad) if bad else "OK: all M3 invariants hold")
    return not bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    if a.check:
        raise SystemExit(0 if check() else 1)
    rows = build()
    if a.json:
        json.dump(rows, open(a.json, "w"), indent=1)
        print("wrote", a.json, len(rows), "rows")
        return
    print("%3s %-9s %-9s %-9s %-5s %s" % ("op", "handler", "fn_x64", "fn_x86", "args", "name"))
    for r in rows:
        print("%3d 0x%05x   0x%05x   0x%05x   %-5s %s"
              % (r["op"], r["handler_x64"], r["fn_x64"], r["fn_x86"],
                 "?" if r["arity"] is None else r["arity"], r["name"] or ""))


if __name__ == "__main__":
    main()
