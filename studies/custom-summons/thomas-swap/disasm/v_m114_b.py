"""V-M1-14 step B: the summon Register continuation chunk + the 0x12940 helper itself."""
import refkit
pe = refkit.load(); fns = refkit.functions(pe); base = refkit.image_base(pe)

def raw(lo, n, label):
    print(f"\n=== RAW {label} from {hex(lo)}")
    for ins in refkit.disasm(pe, lo, lo+n):
        print(f"  {hex(ins.address-base)}: {ins.mnemonic}\t{ins.op_str}")

# chunked continuation of Hi_RegisterSummonModel: does a chunk cover 0x15f3f?
for b,e in fns:
    if b <= 0x15f3f < e:
        print("pdata chunk covering 0x15f3f:", hex(b), hex(e))
raw(0x15f32, 0x40, "summon register continuation")

# The helper claimed to be host->PSX address conversion
f = refkit.func_of(fns, 0x12940)
print("\n0x12940 pdata range:", f and (hex(f[0]), hex(f[1])))
if f:
    raw(f[0], f[1]-f[0], "helper 0x12940 FULL BODY")
