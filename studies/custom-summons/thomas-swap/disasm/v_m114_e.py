"""V-M1-14 step E: (1) 0x7820 head -> [rcx+0x38]=r8 ; (2) who calls 0x7820 ; (3) eff Draw decode;
(4) every write/read of DATA+0x38 in the image; (5) every read of DATA+8."""
import refkit, re
pe = refkit.load(); fns = refkit.functions(pe); base = refkit.image_base(pe)

def raw(lo, hi, label):
    print(f"\n=== {label} [{hex(lo)}..{hex(hi)})")
    for ins in refkit.disasm(pe, lo, hi):
        print(f"  {hex(ins.address-base)}: {ins.mnemonic}\t{ins.op_str}")

f = refkit.func_of(fns, 0x7820)
print("0x7820 pdata:", f and (hex(f[0]), hex(f[1])))
raw(0x7820, 0x7880, "build_world_matrices head")

# call sites of 0x7820 (direct calls: capstone prints absolute target)
tgt = hex(base + 0x7820)
print("\n--- direct callers of 0x7820 ---")
for ins in refkit.iter_instructions(pe, fns):
    if ins.mnemonic == "call" and ins.op_str.strip() == tgt:
        r = ins.address - base
        fo = refkit.func_of(fns, r)
        print(f"  call @ {hex(r)}  in chunk {fo and (hex(fo[0]),hex(fo[1]))}")

# every instruction touching +0x38 as a qword mem operand
print("\n--- qword ptr [reg + 0x38] accesses (image-wide) ---")
pat = re.compile(r"qword ptr \[[a-z0-9]+ \+ 0x38\]")
for ins in refkit.iter_instructions(pe, fns):
    if pat.search(ins.op_str):
        print(f"  {hex(ins.address-base)}: {ins.mnemonic}\t{ins.op_str}")
