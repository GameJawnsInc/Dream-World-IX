import refkit, struct
pe=refkit.load(); fns=refkit.functions(pe)
IB=refkit.image_base(pe); begins=set(b for b,_ in fns)
def sect(rva):
    s=refkit._section_for_rva(pe,rva)
    return s.Name.decode().rstrip('\x00') if s else '?'
d=refkit.read_rva(pe,0x4ab80,0x60*8)
nulls=[]
for i in range(0x28,0x62):
    v=struct.unpack_from("<Q",d,i*8)[0] if i*8+8<=len(d) else struct.unpack_from("<Q",refkit.read_rva(pe,0x4ab80+i*8,8),0)[0]
    rva=v-IB
    if v==0: tag="NULL"; nulls.append(i+0x20)
    elif 0<rva<0x100000: tag="%s%s"%(sect(rva)," FNSTART" if rva in begins else (" mid-fn" if refkit.func_of(fns,rva) else " leaf?"))
    else: tag="NOT-A-VA"
    print("i=%02x raw=%02x %016x %s"%(i,i+0x20,v,tag))
print("NULL raw codes:", " ".join("%02x"%c for c in nulls))
