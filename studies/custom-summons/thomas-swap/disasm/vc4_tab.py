import sys, struct, refkit
pe=refkit.load()
base=int(sys.argv[1],16); n=int(sys.argv[2])
d=pe.get_data(base, n*4)
for i in range(n):
    v=struct.unpack_from('<I', d, i*4)[0]
    print(f"idx 0x{i:02x} -> RVA 0x{v:x}")
