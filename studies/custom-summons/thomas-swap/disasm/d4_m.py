import refkit, struct
pe = refkit.load(); base=refkit.image_base(pe)
jt = struct.unpack('<216I', refkit.read_rva(pe, 0x12358, 216*4))
ft = struct.unpack('<216Q', refkit.read_rva(pe, 0x68780, 216*8))
order = sorted(set(jt))
def op_of(rva):
    best=None
    for op,h in enumerate(jt):
        if h<=rva and (best is None or h>jt[best]): best=op
    return best
for r in (0x12238, 0xf8e2, 0xf906):
    op = op_of(r)
    print(hex(r), "-> op", op, "handler", hex(jt[op]), "fn", hex(ft[op]-base))
# print handler region for those ops
for op in (op_of(0x12238), op_of(0xf8e2), op_of(0xf906)):
    nxt = min([h for h in order if h>jt[op]], default=jt[op]+0x60)
    print("=== op",op,"handler",hex(jt[op]),"..",hex(nxt))
    for i in refkit.disasm(pe, jt[op], nxt): print("   ",hex(i.address-base), i.mnemonic, i.op_str)
