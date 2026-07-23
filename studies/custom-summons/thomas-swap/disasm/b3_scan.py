import sys, refkit
pe = refkit.load()
b,e = int(sys.argv[1],16), int(sys.argv[2],16)
want = ('div','idiv','cvtsi2sd','cvtsi2ss','cvttsd2si','mulsd','divsd','cqo','cdq')
calls=set(); divs=[]; wr16=[]
for ins in refkit.disasm(pe,b,e):
    m=ins.mnemonic
    if m=='call':
        calls.add(ins.op_str)
    if m in want:
        divs.append((ins.address,m,ins.op_str))
    # 16-bit memory writes: mov word ptr [..], reg16
    if m=='mov' and 'word ptr' in ins.op_str and ins.op_str.strip().startswith('word ptr'):
        wr16.append((ins.address,ins.op_str))
print("== calls ==")
for c in sorted(calls): print("  ",c)
print("== div/float ==")
for a,m,o in divs: print(f"  0x{a:x}: {m} {o}")
print(f"== word-writes: {len(wr16)} ==")
for a,o in wr16[:40]: print(f"  0x{a:x}: {o}")
