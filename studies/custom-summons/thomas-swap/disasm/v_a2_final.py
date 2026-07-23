import refkit
pe = refkit.load(); fns = refkit.functions(pe); base = refkit.image_base(pe)

# Continue pose evaluator past the pdata split: linear disasm 0x186b8..0x18760
print("=== pose eval continuation 0x186b8..0x18760 (root build from args) ===")
for ins in refkit.disasm(pe, 0x186b8, 0x18760):
    r = ins.address - base
    t = refkit._rip_target(ins, base)
    extra = f"   -> {hex(t)}" if t is not None else ""
    print(f"  @{hex(r)}: {ins.mnemonic} {ins.op_str}{extra}")

# What is rbx at write#1? scan for rbx set before 0x30cc9
print("\n=== rbx origin in FUNC@0x30c20 (full body up to store) ===")
f = refkit.func_of(fns, 0x30c20)
for ins in refkit.disasm(pe, f[0], f[1]):
    r = ins.address - base
    if r > 0x30cc9: break
    dst = ins.op_str.split(",")[0].strip()
    if dst in ("rbx","ebx","bl") or (ins.mnemonic=="xor" and "bx" in ins.op_str):
        print(f"  @{hex(r)}: {ins.mnemonic} {ins.op_str}")
