import refkit, struct
pe=refkit.load(); fns=refkit.functions(pe)
IB=refkit.image_base(pe)
begins=set(b for b,_ in fns)
def sect(rva):
    s=refkit._section_for_rva(pe,rva)
    return s.Name.decode().rstrip('\x00') if s else '?'
def show(base,lo,hi,label):
    print("=== %s base=%06x idx %d..%d"%(label,base,lo,hi))
    d=refkit.read_rva(pe,base+lo*8,(hi-lo+1)*8)
    for k,i in enumerate(range(lo,hi+1)):
        v=struct.unpack_from("<Q",d,k*8)[0]
        rva=v-IB
        ok=""
        if v==0: ok="NULL"
        elif 0<rva<0x100000:
            ok="%s%s"%(sect(rva), " FNSTART" if rva in begins else " (mid-fn)" if refkit.func_of(fns,rva) else " !!notcode")
        else: ok="NOT-A-VA"
        print("  i=%02x (raw code %02x) %016x rva=%s  %s"%(i,i+0x20,v,hex(rva&0xffffffffffff),ok))
show(0x4aff0,0,0x30,"tableA@0x4aff0")
