import refkit
pe = refkit.load(); base=refkit.image_base(pe)
fns = refkit.functions(pe)
idx = refkit.xref_index(pe, 0x220F00, 0x220F08, fns)
for t,v in idx.items():
    print(hex(t), [(hex(a),m,o) for a,m,o in v])
print("--- refs to installed camera 0x69730")
idx2 = refkit.xref_index(pe, 0x69730, 0x69760, fns)
for t,v in sorted(idx2.items()):
    print(hex(t), [(hex(a),m,o) for a,m,o in v])
