"""V-M1-07 step L: (1) confirm shl rcx,5 @0x16917 (bone stride) in DrawEffModelByBone.
(2) who WRITES the packet cursor [gpuctx+0x24]? is it reset per frame (probe-read lifetime)?"""
import re
import refkit
pe = refkit.load()
fns = refkit.functions(pe)
B = refkit.image_base(pe)

print("=== (1) DrawEffModelByBone 0x168e0..0x16990 ===")
for ins in refkit.disasm(pe, 0x168E0, 0x16990):
    print(f"  {hex(ins.address-B)}: {ins.mnemonic}\t{ins.op_str}")

print("\n=== (2) stores to dword [reg + 0x24] in fns that also load 0x66c68 ===")
# collect fns that reference 0x66c68
ref_fns = set()
for frm, _, _ in refkit.xrefs_to(pe, 0x66C68, fns):
    f = refkit.func_of(fns, frm)
    if f:
        ref_fns.add(f)
PAT = re.compile(r"^dword ptr \[(?!rsp)(r[a-z0-9]+) \+ 0x24\],")
for f in sorted(ref_fns):
    for ins in refkit.disasm(pe, f[0], f[1]):
        if ins.mnemonic == "mov" and PAT.match(ins.op_str):
            print(f"  {hex(ins.address-B)}  fn {hex(f[0])}  mov {ins.op_str}")
