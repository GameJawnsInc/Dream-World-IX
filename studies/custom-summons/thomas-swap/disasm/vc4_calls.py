import sys, refkit, re
pe=refkit.load(); fns=refkit.functions(pe); IB=0x180000000
targets=set(int(a,16)+IB for a in sys.argv[1:])
for b,e in fns:
    for ins in refkit.disasm(pe,b,e):
        if ins.mnemonic in ("call","jmp","lea"):
            m=re.match(r'^0x([0-9a-f]+)$', ins.op_str)
            if m and int(m.group(1),16) in targets:
                print("in fn",hex(b),"@",hex(ins.address-IB), ins.mnemonic, ins.op_str)
