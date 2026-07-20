"""TXT LENS: locate title UI prefab + Localization table across ALL bundles.
Scans container paths for embeddedasset/ui/manifest/title/localis needles."""
import os, time, glob
import UnityPy

SA = r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX\StreamingAssets"
NEEDLES = ["embeddedasset", "/ui/", "manifest", "title", "localis", "localiz", "/text/"]
bundles = sorted(glob.glob(os.path.join(SA, "p0data*.bin")))
DEADLINE = time.time() + 115
per_needle_first = {}
for b in bundles:
    if time.time() > DEADLINE:
        print("TIME BUDGET HIT after", os.path.basename(b)); break
    try:
        env = UnityPy.load(b); cont = env.container
    except Exception as e:
        print(f"  !{os.path.basename(b)}: {e}"); continue
    counts = {n:0 for n in NEEDLES}
    samples = {n:None for n in NEEDLES}
    for path in cont.keys():
        pl = path.lower()
        for n in NEEDLES:
            if n in pl:
                counts[n]+=1
                if samples[n] is None: samples[n]=path
    hot = {n:(counts[n],samples[n]) for n in NEEDLES if counts[n]}
    if hot:
        print(f"--- {os.path.basename(b)} ({len(cont)} cont):")
        for n,(c,s) in hot.items():
            print(f"      {n}: {c}  e.g. {s}")
print("done")
