import os, glob, collections
exec(open('vc4_corpus.py').read().split("files = sorted")[0])
SCR=r"C:\gd\SCRATCH\summon-format"
files=sorted(glob.glob(os.path.join(SCR,"ef*.bytes")))
bad=[]; maxarg=collections.Counter()
for f in files:
    blob=open(f,'rb').read(); ch,_,_=walk(blob); seq=sequence(blob)
    n03=sum(1 for (_,c,_,_) in seq if c==0x03)
    loads=[a1 for (_,c,a1,_) in seq if c==0x05]
    if n03 != len(ch)-1: bad.append((os.path.basename(f), len(ch), n03))
    if loads and max(loads) >= len(ch): maxarg[os.path.basename(f)]=(max(loads), len(ch))
    # LOAD arg order check: are load args exactly the ordinals in increasing order?
print("files where #(op 0x03) != chunkCount-1:", len(bad), bad[:10])
print("files where a LOAD_CHUNK arg >= chunkCount:", dict(maxarg))
# distinct LOAD args seen
argc=collections.Counter()
for f in files:
    blob=open(f,'rb').read()
    for (_,c,a1,a2) in sequence(blob):
        if c==0x05: argc[a1]+=1
print("LOAD_CHUNK arg histogram:", dict(sorted(argc.items())))
