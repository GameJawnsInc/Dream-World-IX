import refkit
pe = refkit.load(); fns = refkit.functions(pe); base = refkit.image_base(pe)

def window(fn_start, lo, hi, label):
    f = refkit.func_of(fns, fn_start)
    print(f"\n=== {label}  FUNC[{hex(f[0])}..{hex(f[1])}] window [{hex(lo)}..{hex(hi)}] ===")
    for ins in refkit.disasm(pe, f[0], f[1]):
        r = ins.address - base
        if lo <= r <= hi:
            t = refkit._rip_target(ins, base)
            extra = f"   -> {hex(t)}" if t is not None else ""
            print(f"  @{hex(r)}: {ins.mnemonic} {ins.op_str}{extra}")

# Write#1 context: what is rbx (the value stored into rec[0].data)?  Look before 0x30cc9.
window(0x30c20, 0x30c90, 0x30ce0, "WRITE#1 alloc store (rec[0].data = rbx)")

# Write#2 context: is r12 zero at 0xf90d?
window(0xeea4, 0xf8e0, 0xf920, "WRITE#2 clear (rec[0].data = r12)")

# Getter: GetSummonBonePos @0x185b0 -- does it deref [rec+0]+0x38 ?
window(0x185b0, 0x185b0, 0x18625, "GetSummonBonePos (bones @ DATA+0x38)")

# Getter: GetSummonBoneMatrix @0x18630
window(0x18630, 0x18630, 0x18692, "GetSummonBoneMatrix (full 32B copy)")
