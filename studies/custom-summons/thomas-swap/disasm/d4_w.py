import refkit
pe = refkit.load(); base=refkit.image_base(pe)
ins=list(refkit.disasm(pe, 0x14c30, 0x15055))
print("count",len(ins))
for i in ins[:45]: print(hex(i.address-base), i.mnemonic, i.op_str)
print("...")
for i in ins:
    a=i.address-base
    if i.mnemonic in ('mov','movsx') and ('[rbx' in i.op_str or '[rdi' in i.op_str) and i.op_str.split(',')[0].strip().startswith(('word','dword')):
        print(hex(a), i.mnemonic, i.op_str)
