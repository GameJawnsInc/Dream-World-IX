import sys, collections
log=r"C:/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX/sfxmeshprobe.log"
rows=collections.OrderedDict()
dupdiff=0
with open(log,'r',errors='ignore') as f:
    for ln in f:
        if not ln.startswith('ROOT,'): continue
        p=ln.strip().split(',')
        fr=int(p[2]); vals=tuple(int(x) for x in p[3:])
        if fr in rows and rows[fr]!=vals: dupdiff+=1
        rows[fr]=vals
frames=sorted(rows)
print(f"distinct frames with a ROOT row: {len(frames)}  range {frames[0]}..{frames[-1]}  intra-frame disagreements: {dupdiff}")
zero=[f for f in frames if all(v==0 for v in rows[f][1:])]
nz=[f for f in frames if not all(v==0 for v in rows[f][1:])]
print(f"all-zero root frames: {len(zero)}  (first {zero[:3]} last {zero[-3:] if zero else []})")
print(f"non-zero root frames: {len(nz)}  (first {nz[:3]} last {nz[-3:] if nz else []})")
if nz:
    uniq=collections.Counter(rows[f] for f in nz)
    print(f"distinct non-zero root VALUES: {len(uniq)}")
    for v,c in uniq.most_common(12):
        print(f"   n={c:4d}  rot={v[1:10]}  t={v[10:]}")
    # transitions
    prev=None
    print("  transitions (frame -> new value):")
    n=0
    for f in frames:
        if rows[f]!=prev:
            print(f"    f{f:4d}  rot={rows[f][1:10]} t={rows[f][10:]}")
            prev=rows[f]; n+=1
            if n>25: print("    ..."); break
