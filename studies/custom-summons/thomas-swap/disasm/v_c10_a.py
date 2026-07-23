"""C10 verification step A: fresh disassembly of the three cited x64 functions.

fn 0x48b10 (the >=0x20 opcode router), fn 0x49170 (the 0x80+N handler),
fn 0xd820 (the program launcher). Prints the .pdata bounds so we can tell a real
body from a cold error funclet, then the full body.
"""
import sys
import refkit

pe = refkit.load()
fns = refkit.functions(pe)
base = refkit.image_base(pe)

targets = [int(x, 16) for x in (sys.argv[1:] or ["48b10", "49170", "d820"])]
for t in targets:
    f = refkit.func_of(fns, t)
    print("=" * 78)
    print(f"target rva {hex(t)}  pdata range {None if not f else (hex(f[0]), hex(f[1]))}"
          f"  size={None if not f else f[1]-f[0]}")
    if not f:
        print("  NOT COVERED BY .pdata")
        continue
    for ins in refkit.disasm(pe, f[0], f[1]):
        print(f"  {hex(ins.address - base)}: {ins.mnemonic:8s} {ins.op_str}")
