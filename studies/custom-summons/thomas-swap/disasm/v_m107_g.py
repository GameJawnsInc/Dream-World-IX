"""V-M1-07 step G: DrawSummonModel -- locate real body, verify r8 provenance for the 0x7820 call."""
import refkit
pe = refkit.load()
fns = refkit.functions(pe)
info = refkit.locate_function(pe, "Hi_DrawSummonModel", fns)
print("DrawSummonModel:", info["name"], "str", hex(info["string_rva"]),
      "xrefs", [hex(x) for x in info["xrefs"]],
      "funcs", [(hex(a), hex(b)) for a, b in info["all_funcs"]])
f = refkit.func_of(fns, 0x17740)
print("func_of(0x17740) =", (hex(f[0]), hex(f[1])), "size", f[1]-f[0])
print("\n--- 0x17740..0x17890 ---")
for ins in refkit.disasm(pe, 0x17740, 0x17890):
    print(f"  {hex(ins.address-0x180000000)}: {ins.mnemonic}\t{ins.op_str}")
