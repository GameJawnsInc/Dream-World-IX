import collections, os
exec(open('vc4_corpus.py').read().split("files = sorted")[0])
import glob
SCR = r"C:\gd\SCRATCH\summon-format"
for name in ['ef225','ef227','ef251','ef381','ef447']:
    f=os.path.join(SCR,name+'.bytes'); blob=open(f,'rb').read()
    ch,_,_=walk(blob)
    pt=[programs(blob,c) for c in ch]
    print("==",name,"chunks",len(ch),"idxField",[c['idxField'] for c in ch])
    for i,p in enumerate(pt):
        live=[k for k,v in enumerate(p['progs']) if v] if p else None
        print("   chunk",i,"headerRel",hex(p['headerRel']),"liveProgs",live)
    seq=sequence(blob)
    ev=[(hex(o),hex(c),a1,a2) for (o,c,a1,a2) in seq if c==0x05 or c>=0x80 or c==0x03]
    print("   seq events (03=next,05=load,>=80=run):", ev)
