import struct, sys, collections
path=sys.argv[1]; b=open(path,'rb').read()
tgts=[int(x,16) for x in sys.argv[2:]]
# index every u32 in the file by value
pos=collections.defaultdict(list)
for o in range(0, len(b)-4, 4):
    pos[struct.unpack_from('<I',b,o)[0]].append(o)
# for a candidate constant K, motion at M would be stored as M+K (mod 2^32)
cand=collections.Counter()
for t in tgts:
    for v,ol in pos.items():
        k=(v-t)&0xFFFFFFFF
        cand[k]+=1
best=[(k,c) for k,c in cand.items() if c>=6]
best.sort(key=lambda x:-x[1])
for k,c in best[:12]:
    locs=[]
    for t in tgts:
        v=(t+k)&0xFFFFFFFF
        locs.append(pos.get(v,[None])[0])
    print(f"K={k:#010x} matches={c} locations={[hex(l) if l is not None else None for l in locs]}")
