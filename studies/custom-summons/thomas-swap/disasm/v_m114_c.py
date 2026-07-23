"""V-M1-14 step C: full 0x12940 helper (all chunks) + summon register cont + modelDesc+0x3c origin."""
import refkit
pe = refkit.load(); fns = refkit.functions(pe); base = refkit.image_base(pe)

def raw(lo, hi, label):
    print(f"\n=== {label} [{hex(lo)}..{hex(hi)})")
    for ins in refkit.disasm(pe, lo, hi):
        print(f"  {hex(ins.address-base)}: {ins.mnemonic}\t{ins.op_str}")

# chunks adjacent to 0x12940
print("pdata chunks 0x12900-0x12b00:", [(hex(b),hex(e)) for b,e in fns if 0x12900<=b<0x12b00])
raw(0x12940, 0x129e0, "helper 0x12940 + following chunk")
raw(0x15f42, 0x15fda, "Hi_RegisterSummonModel chunk2 (motion field)")
print("\npdata chunks near 0x47330:", [(hex(b),hex(e)) for b,e in fns if 0x47280<=b<0x474ff])
raw(0x47380, 0x473d0, "modelDesc+0x3c origin (cited 0x473a0/0x473a5)")
