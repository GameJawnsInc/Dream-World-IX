import sys, refkit
pe = refkit.load()
fns = refkit.functions(pe)
def find(rva):
    for (b,e) in fns:
        if b <= rva < e:
            return (b,e)
    return None
for a in sys.argv[1:]:
    rva = int(a,16)
    r = find(rva)
    if r: print(f"0x{rva:x} -> FUNC[0x{r[0]:x}..0x{r[1]:x}] ({r[1]-r[0]} bytes)")
    else: print(f"0x{rva:x} -> NOT in .pdata")
