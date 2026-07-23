"""V-M1-07 step I: REFUTATION SWEEP.
(a) every store to qword [reg+0x38] in the image -> is 0x7842 the ONLY writer of DATA+0x38?
(b) every reference to the packet-cursor global 0x66c68 -> is it a per-frame-reset bump allocator?
"""
import re
import refkit

pe = refkit.load()
fns = refkit.functions(pe)
BASE = refkit.image_base(pe)

STORE = re.compile(r"^qword ptr \[(r[a-z0-9]+) \+ 0x38\], (r[a-z0-9]+)$")
print("=== (a) stores to qword [reg+0x38] ===")
n = 0
for ins in refkit.iter_instructions(pe, fns):
    if ins.mnemonic != "mov":
        continue
    m = STORE.match(ins.op_str)
    if m:
        n += 1
        f = refkit.func_of(fns, ins.address - BASE)
        print(f"  {hex(ins.address-BASE)}  in fn {hex(f[0]) if f else '?'}   mov {ins.op_str}")
print("  total:", n)

print("\n=== (b) rip-refs to 0x66c68 ===")
for frm, mn, ops in refkit.xrefs_to(pe, 0x66C68, fns):
    f = refkit.func_of(fns, frm)
    print(f"  {hex(frm)}  fn {hex(f[0]) if f else '?'}   {mn} {ops}")
