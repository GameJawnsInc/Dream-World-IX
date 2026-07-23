import refkit,struct
pe=refkit.load('x86'); IB=refkit.image_base(pe)
r=refkit.find_string(pe,"HIRAISHI ERROR")
print("x86 'HIRAISHI ERROR' string rva",hex(r), "imagebase",hex(IB))
# walk backwards from the string looking for a run of .text pointers (4-byte)
def sec(rva):
    s=refkit._section_for_rva(pe,rva); return s.Name.decode().rstrip('\x00') if s else '?'
text=[s for s in pe.sections if s.Name.startswith(b'.text')][0]
tlo,thi=text.VirtualAddress,text.VirtualAddress+text.Misc_VirtualSize
start=r-4*40
d=refkit.read_rva(pe,start,4*40)
run=[]
for i in range(40):
    v=struct.unpack_from("<I",d,i*4)[0]; rva=v-IB
    ok = tlo<=rva<thi
    run.append((hex(start+i*4),hex(v),"TEXT" if ok else ("NULL" if v==0 else "-")))
for x in run[-24:]: print(x)
