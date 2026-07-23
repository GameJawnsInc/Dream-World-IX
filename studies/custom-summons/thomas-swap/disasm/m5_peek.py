import struct,sys
b=open(sys.argv[1],'rb').read()
o=int(sys.argv[2],16); n=int(sys.argv[3],0)
for i in range(0,n,16):
    row=b[o+i:o+i+16]
    print(f"{o+i:#08x}  " + " ".join(f"{x:02x}" for x in row))
