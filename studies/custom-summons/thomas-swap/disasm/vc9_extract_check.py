import UnityPy, hashlib, glob, os, sys
G=r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX"
cands=[os.path.join(G,"x64","FF9_Data","resources.assets"),os.path.join(G,"x64","FF9_Data","sharedassets0.assets")]
targets={"ef227","ef038","ef000"}
found={}
count=0
for c in cands:
    if not os.path.exists(c): continue
    env=UnityPy.load(c)
    for o in env.objects:
        if o.type.name!="TextAsset": continue
        try: d=o.read()
        except Exception: continue
        n=getattr(d,"m_Name",None) or getattr(d,"name","")
        if n.startswith("ef") and len(n)==5 and n[2:].isdigit():
            count+=1
            if n in targets:
                raw=d.m_Script.encode("utf-8","surrogateescape") if isinstance(d.m_Script,str) else bytes(d.m_Script)
                found[n]=(len(raw),hashlib.sha256(raw).hexdigest())
    print(c,"-> running count",count)
for n in sorted(found):
    p=os.path.join("C:/gd/SCRATCH/summon-format",n+".bytes")
    dsk=open(p,'rb').read()
    print(n,"asset",found[n][0],found[n][1][:16],"| disk",len(dsk),hashlib.sha256(dsk).hexdigest()[:16],"MATCH" if hashlib.sha256(dsk).hexdigest()==found[n][1] else "DIFFER")
print("total ef### TextAssets in install:",count)
