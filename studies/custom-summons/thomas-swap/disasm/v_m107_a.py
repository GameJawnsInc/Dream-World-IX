"""V-M1-07 step A: locate build_world_matrices@0x7820 and disassemble its head + rigid path."""
import refkit

pe = refkit.load()
fns = refkit.functions(pe)
f = refkit.func_of(fns, 0x7820)
print("func_of(0x7820) =", None if not f else (hex(f[0]), hex(f[1])), "size", None if not f else f[1]-f[0])

# head: first 60 instructions
print("\n--- HEAD 0x7820.. ---")
for i, ins in enumerate(refkit.disasm(pe, f[0], f[1])):
    if i >= 70:
        break
    print(f"  {hex(ins.address-0x180000000)}: {ins.mnemonic}\t{ins.op_str}")
