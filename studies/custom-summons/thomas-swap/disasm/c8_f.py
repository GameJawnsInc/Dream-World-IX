import refkit, struct
pe=refkit.load()
base=0x66c70
data=pe.get_data(base, 0x38*80)
def rd(off,n): return int.from_bytes(data[off:off+n],'little')
print("stride 0x38 entries from %x"%base)
i=0
while i<80:
    off=i*0x38
    mask=rd(off,4); match=rd(off+4,4)
    sub=rd(off+0x10,8); b30=rd(off+0x30,1)
    nxt=rd(off+0x38,4) if off+0x38+4<=len(data) else 0
    print("%2d @%05x mask=%08x match=%08x sub=%016x b30=%02x  raw8_c=%s"%(i,base+off,mask,match,sub,b30,data[off+8:off+0x10].hex()))
    if nxt==0: break
    i+=1
