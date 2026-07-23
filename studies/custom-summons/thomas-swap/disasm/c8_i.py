import refkit, struct
pe=refkit.load(); TB=0x66c70
i=0; rows=[]
while True:
    d=pe.get_data(TB+i*0x38,0x38); m,mt=struct.unpack_from("<II",d,0)
    if m==0: break
    rows.append((i,m,mt,d[0x30])); i+=1
print("total decode entries:", len(rows))
for r in rows[80:]:
    print("%2d mask=%08x match=%08x b30=%02x"%r)
print()
print("=== pre-decoder tail 0xd2c0..0xd36c ===")
for ins in refkit.disasm(pe,0xd2c0,0xd36c): print("%05x  %-10s %s"%(ins.address,ins.mnemonic,ins.op_str))
