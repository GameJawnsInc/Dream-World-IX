import refkit
pe = refkit.load(); fns = refkit.functions(pe); base = refkit.image_base(pe)

# Pose evaluator @0x186a0: does it build root at DATA+0x40, from ARGS (rdx/r8)?
f = refkit.func_of(fns, 0x186a0)
print(f"=== pose evaluator FUNC[{hex(f[0])}..{hex(f[1])}] ===")
for ins in refkit.disasm(pe, f[0], f[1]):
    r = ins.address - base
    if r > 0x18760: break
    t = refkit._rip_target(ins, base)
    extra = f"   -> {hex(t)}" if t is not None else ""
    print(f"  @{hex(r)}: {ins.mnemonic} {ins.op_str}{extra}")

# Is r12 the function's zero-register at the clear site? scan 0xeea4.. for xor r12,r12
print("\n=== r12 zeroing sites in clear FUNC[0xeea4..] ===")
f = refkit.func_of(fns, 0xeea4)
for ins in refkit.disasm(pe, f[0], f[1]):
    if ins.mnemonic in ("xor","mov") and "r12" in ins.op_str:
        r = ins.address - base
        if "r12, r12" in ins.op_str or ("r12" in ins.op_str.split(",")[0] and ins.mnemonic=="xor"):
            print(f"  @{hex(r)}: {ins.mnemonic} {ins.op_str}")
        if r >= 0xf900 and r <= 0xf910:
            print(f"  (near clear) @{hex(r)}: {ins.mnemonic} {ins.op_str}")

# Adversarial: is DATA ptr from a heap alloc in write#1? trace rbx before 0x30cc9
print("\n=== WRITE#1 pre-store: where does rbx come from? (scan FUNC start..0x30cc9) ===")
f = refkit.func_of(fns, 0x30c20)
for ins in refkit.disasm(pe, f[0], f[1]):
    r = ins.address - base
    if r > 0x30cc9: break
    if ("rbx" in ins.op_str and ins.mnemonic in ("mov","lea","call","xor")) or ins.mnemonic=="call":
        t = refkit._rip_target(ins, base)
        extra = f"   -> {hex(t)}" if t is not None else ""
        print(f"  @{hex(r)}: {ins.mnemonic} {ins.op_str}{extra}")
