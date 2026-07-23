import refkit
pe=refkit.load()
for rva in (0x2208d0,0x3208d0,0x320cd0,0x3678f0,0x323198):
    s=refkit._section_for_rva(pe,rva)
    nm=s.Name.decode().rstrip('\x00')
    # is it within raw data?
    inraw = rva - s.VirtualAddress < s.SizeOfRawData
    try: d=refkit.read_rva(pe,rva,32)
    except Exception as e: d=b''
    print("%08x %-8s inRaw=%s rawSize=%x virtSize=%x bytes=%s"%(rva,nm,inraw,s.SizeOfRawData,s.Misc_VirtualSize,d.hex()))
print()
print("writers/readers of 0x2208d0:")
for fr,mn,ops in refkit.xrefs_to(pe,0x2208d0):
    f=refkit.func_of(refkit.functions(pe),fr)
    print("  from %06x in fn %s : %s %s"%(fr, f and hex(f[0]), mn, ops))
