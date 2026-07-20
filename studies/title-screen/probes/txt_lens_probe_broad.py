"""TXT LENS: broad container-key scan of FF9 bundles."""
import os, time, glob
import UnityPy

SA = r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX\StreamingAssets"
NEEDLES = ["title", "localiz", "newgame", "new_game", "continue"]
bundles = sorted(glob.glob(os.path.join(SA, "p0data*.bin")))
DEADLINE = time.time() + 110
printed_sample = 0
for b in bundles:
    if time.time() > DEADLINE:
        print("TIME BUDGET HIT"); break
    try:
        env = UnityPy.load(b)
        cont = env.container
    except Exception as e:
        print(f"  !{os.path.basename(b)}: {e}"); continue
    n = len(cont)
    if printed_sample < 3 and n:
        keys = list(cont.keys())
        print(f"--- {os.path.basename(b)} has {n} containers; sample:")
        for k in keys[:8]:
            print("     ", k)
        printed_sample += 1
    for path, obj in cont.items():
        pl = path.lower()
        if any(nd in pl for nd in NEEDLES):
            try: t = obj.type.name
            except Exception: t = "?"
            print(f"[{os.path.basename(b)}] {t}  {path}")
print("done")
