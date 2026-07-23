import sys, refkit
pe = refkit.load()
IB = 0x180000000
mm = pe.get_memory_mapped_image()
fns = refkit.functions(pe)
def owner(rva):
    for (b,e) in fns:
        if b<=rva<e: return (b,e)
    return None
def read_qword(rva):
    try:
        return int.from_bytes(mm[rva:rva+8],'little')
    except Exception:
        return None
b,e = int(sys.argv[1],16), int(sys.argv[2],16)
rows=[]
for ins in refkit.disasm(pe,b,e):
    if ins.mnemonic=='call' and 'rip +' in ins.op_str and 'qword' in ins.op_str:
        try:
            disp = int(ins.op_str.split('rip +')[1].rstrip(']').strip(),16)
        except Exception:
            continue
        tabrva = ins.address + ins.size + disp - IB
        q = read_qword(tabrva)
        tgt = (q-IB) if (q and q>=IB) else q
        rows.append((ins.address-IB, tabrva, tgt))
# unique targets
from collections import Counter
tc = Counter(r[2] for r in rows)
print(f"{len(rows)} indirect calls; unique targets:")
for tgt,n in tc.most_common():
    o = owner(tgt) if tgt else None
    os = f"FUNC[0x{o[0]:x}..0x{o[1]:x}]" if o else "?"
    print(f"  fn 0x{tgt:x}  x{n}  {os}")
