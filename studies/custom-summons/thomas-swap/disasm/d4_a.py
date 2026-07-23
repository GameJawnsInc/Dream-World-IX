import refkit, struct
pe = refkit.load()
for rva in (0x187e0, 0x18840):
    print("=== xrefs to", hex(rva))
    try:
        print([hex(x) for x in refkit.xrefs_to(pe, rva)])
    except Exception as e:
        print("ERR", e)
print("=== Hi_HideSummonModelMesh 0x18840")
for i in refkit.disasm(pe, 0x18840, 0x188a0):
    print(i)
print("=== Hi_ShowSummonModelMesh 0x187e0")
for i in refkit.disasm(pe, 0x187e0, 0x18840):
    print(i)
