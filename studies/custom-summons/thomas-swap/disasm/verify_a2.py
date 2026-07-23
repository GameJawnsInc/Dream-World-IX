import refkit

pe = refkit.load()
fns = refkit.functions(pe)

def func_of(rva):
    for b,e in fns:
        if b <= rva < e:
            return b,e
    return None

# cited RVAs -> label
cites = {
    0x15f3f: "+0x08 modelId Register",
    0x17a3b: "+0x10 motion SetSummonMotion",
    0x17776: "+0x10 motion Draw",
    0x1880e: "+0x20 hideMask Show",
    0x1886c: "+0x20 hideMask Hide",
    0x185d3: "+0x38 bones GetBonePos",
    0x18653: "+0x38 bones GetBoneMatrix",
    0x186b2: "+0x40 root pose-eval",
    0x188cb: "+0x70 texAnim StartTexAnim",
}

for rva,label in cites.items():
    fb = func_of(rva)
    print("="*70)
    print(f"CITE {label}  rva=0x{rva:x}  func={('0x%x..0x%x'%fb) if fb else 'NONE(.pdata)'}")
    if not fb:
        # disasm a window anyway from the nearest lower function start
        cands = [b for b,e in fns if b<=rva]
        b = max(cands); e = min([x for x in [ee for bb,ee in fns if bb==b]] )
        fb=(b,e)
    b,e = fb
    for ins in refkit.disasm(pe, b, e):
        mark = " <<<" if (ins.address - refkit.image_base(pe)) == rva else ""
        if abs((ins.address-refkit.image_base(pe)) - rva) <= 40 or mark:
            print(f"  0x{ins.address-refkit.image_base(pe):06x}: {ins.mnemonic} {ins.op_str}{mark}")
