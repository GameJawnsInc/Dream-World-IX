"""V-M1-10: independent caller/callee index for the shared-pipeline claim.

Builds, from a fresh per-function disassembly (.pdata-driven, no linear sweep), a map
    target_rva -> [(from_rva, containing_function_begin), ...]
for every DIRECT `call`/`jmp` whose operand is an absolute address inside the image.
"""
import sys, collections
import refkit


def build(arch="x64"):
    pe = refkit.load(arch)
    fns = refkit.functions(pe) if arch == "x64" else None
    base = refkit.image_base(pe)
    calls = collections.defaultdict(list)   # target -> [(from, fnbegin)]
    if arch == "x64":
        md = refkit._md(pe)
        for b, e in fns:
            try:
                code = refkit.read_rva(pe, b, e - b)
            except Exception:
                continue
            for ins in md.disasm(code, base + b):
                if ins.mnemonic in ("call", "jmp") and ins.op_str.startswith("0x"):
                    try:
                        t = int(ins.op_str, 16) - base
                    except ValueError:
                        continue
                    calls[t].append((ins.address - base, b, ins.mnemonic))
    return pe, fns, calls


if __name__ == "__main__":
    pe, fns, calls = build()
    for a in sys.argv[1:]:
        t = int(a, 16)
        print(f"== callers of 0x{t:x}: {len(calls.get(t,[]))}")
        for frm, fb, mn in sorted(calls.get(t, [])):
            print(f"   {mn} @0x{frm:x}   (inside fn 0x{fb:x})")
