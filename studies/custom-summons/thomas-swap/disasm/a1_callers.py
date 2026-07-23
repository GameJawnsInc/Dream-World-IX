"""A1: find the direct callers of each summon-subsystem entry + scan for fn-pointer tables."""
import sys, re
sys.path.insert(0, r'C:/gd/Dream-World-IX/.claude/worktrees/unruffled-moser-861897/studies/custom-summons/thomas-swap/disasm')
import refkit
pe = refkit.load(); fns = refkit.functions(pe); base = refkit.image_base(pe)
absimm = re.compile(r'^0x([0-9a-f]+)$')
def fb(rva):
    f = refkit.func_of(fns, rva); return f[0] if f else None

# reverse call graph over ALL disassemblable functions (incl below .pdata via manual add)
# add the export bodies as pseudo-functions so we can traverse them
extra = [(0x13a0,0x1630),(0x1630,0x1800),(0x1800,0x1cf0),(0x1e80,0x1f00)]
allfns = sorted(set(fns) | set(extra))

cf_in = {}
for ins in refkit.iter_instructions(pe, allfns):
    if ins.mnemonic=='call' or ins.mnemonic.startswith('j'):
        mm = absimm.match(ins.op_str.strip())
        if mm:
            src=fb(ins.address-base); trva=int(mm.group(1),16)-base
            # map src through extra ranges too
            for (b,e) in extra:
                if b<=ins.address-base<e: src=b
            cf_in.setdefault(trva,[]).append((ins.address-base, src, ins.mnemonic))

ENTRIES = {
 0x16837:"BIG-1097(byBone/matrix)",0x171ef:"BIG-358(morphByBone)",0x17710:"DrawSummon-entry",
 0x17a10:"SetSummonMotion",0x17a70:"SetSummonMotFrame",0x185b0:"GetSummonBonePos",
 0x18630:"GetSummonBoneMatrix",0x187e0:"ShowMesh",0x18840:"HideMesh",0x188a0:"StartTexAnim",
 0x18930:"StopTexAnim",0x18af0:"ModAbr",0x18b50:"ModRGB",0x16112:"RegSummon-stub",
 0x1606c:"RegSummon-body?",0x15ee0:"summon-helper-85B",0x186a0:"helper-24B",
}
print("### direct callers of each summon entry")
for e,lbl in ENTRIES.items():
    cs = cf_in.get(e,[])
    print(f"\n-- {hex(e)} {lbl}: {len(cs)} caller(s)")
    for frm,src,mn in cs:
        srcf = f"in {hex(src)}" if src is not None else "in ?"
        print(f"     {mn} from {hex(frm)} {srcf}")

# scan .rdata for absolute qword pointers to any summon entry (dispatch table)
print("\n### absolute-qword fn-pointer table scan (entries stored as data)")
data = pe.__data__
targets = {v:k for k,v in {**ENTRIES}.items()}  # not used
want = set(ENTRIES) | {0x185b0,0x18630}
# search image for little-endian VA = base+entry
for e in sorted(want):
    va = (base+e).to_bytes(8,'little')
    off = data.find(va)
    hits=[]
    start=0
    while True:
        i = data.find(va, start)
        if i<0: break
        # file offset -> rva
        for s in pe.sections:
            if s.PointerToRawData<=i<s.PointerToRawData+s.SizeOfRawData:
                hits.append(s.VirtualAddress+(i-s.PointerToRawData)); break
        start=i+1
    if hits: print(f"   {hex(e)} {ENTRIES[e]}: fn-ptr stored at rva {[hex(h) for h in hits]}")
