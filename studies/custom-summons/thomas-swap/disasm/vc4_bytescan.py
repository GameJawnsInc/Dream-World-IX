import sys, struct, refkit
pe = refkit.load()
IB = pe.OPTIONAL_HEADER.ImageBase
targets = [int(a,16) for a in sys.argv[1:]]
for sec in pe.sections:
    name = sec.Name.rstrip(b'\x00').decode()
    data = sec.get_data()
    base = sec.VirtualAddress
    if name not in ('.text',): continue
    for i in range(0, len(data)-4):
        d = struct.unpack_from('<i', data, i)[0]
        for extra in (0,1,2,4):
            tgt = base + i + 4 + extra + d
            if tgt in targets:
                print(name, "dispAt RVA", hex(base+i), "extra", extra, "-> target", hex(tgt))
