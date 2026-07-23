import os, glob, collections, itertools, random
exec(open('vc4_corpus.py').read().split("files = sorted")[0])
SCR = r"C:\gd\SCRATCH\summon-format"
files = sorted(glob.glob(os.path.join(SCR,"ef*.bytes")))

# corpus opcode totals (independent of the claim, for comparison with M2's 11,807)
tot=0; mx=0; endok=0; codes=collections.Counter()
for f in files:
    blob=open(f,'rb').read(); seq=sequence(blob)
    tot+=len(seq); mx=max(mx,len(seq))
    if seq and seq[-1][1]==0: endok+=1
    for (_,c,_,_) in seq: codes[c]+=1
print("total seq opcodes:",tot,"max ops in a file:",mx,"files ending in 0x00:",endok)
print("distinct codes:",len(codes), "0x80+N count:", sum(v for k,v in codes.items() if k>=0x80))

# NULL TEST: is the ordinal key non-vacuous? permute chunk assignment in multi-chunk files.
print()
print("=== null test: random chunk permutations (multi-chunk files only) ===")
random.seed(7)
for name in ['ef225','ef227','ef251','ef381','ef447']:
    blob=open(os.path.join(SCR,name+'.bytes'),'rb').read()
    ch,_,_=walk(blob); pt=[programs(blob,c) for c in ch]
    n=len(ch)
    def fails_for(perm):
        cur=0; f=0; tot=0
        for (p,c,a1,a2) in sequence(blob):
            if c==0x05: cur = perm[a1] if a1<n else None
            elif c>=0x80:
                tot+=1
                N=c-0x80
                if cur is None or pt[cur] is None or pt[cur]['progs'][N]==0: f+=1
        return f,tot
    ident=list(range(n))
    f0,t0=fails_for(ident)
    trials=[]
    perms = list(itertools.permutations(range(n))) if n<=6 else [random.sample(range(n),n) for _ in range(2000)]
    for pm in perms:
        if list(pm)==ident: continue
        trials.append(fails_for(list(pm))[0])
    clean=sum(1 for x in trials if x==0)
    print(f"{name}: n={n} ops={t0} identity-fails={f0}  perms tested={len(trials)} perms with 0 fails={clean} ({100*clean/max(1,len(trials)):.1f}%)")
