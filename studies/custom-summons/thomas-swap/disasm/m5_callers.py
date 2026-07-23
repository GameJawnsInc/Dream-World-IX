import sys, refkit
pe = refkit.load(sys.argv[2] if len(sys.argv)>2 else 'x64'); base=refkit.image_base(pe); fns=refkit.functions(pe)
tgt = int(sys.argv[1],16)
import re
for ins in refkit.iter_instructions(pe, fns):
    if ins.mnemonic in ('call','jmp') and ins.op_str.startswith('0x'):
        try: t = int(ins.op_str,16)-base
        except: continue
        if t==tgt:
            print(f"{ins.address-base:#x}  {ins.mnemonic} {t:#x}")
