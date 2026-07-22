"""
GAP probe 1: locate the 'music033' container in FF9's sound bundles so the exact
loose-override path is confirmed. Time-boxed: only opens bundles whose name looks
like a sound bundle, and stops after finding music033.

READ-ONLY. Run: py probe_music033_container.py
"""
import os, glob, time
import UnityPy

SA = r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX\StreamingAssets"
bins = sorted(glob.glob(os.path.join(SA, "p0data*.bin")))
print("bundles found:", len(bins))
hits = []
start = time.time()
for path in bins:
    if time.time() - start > 240:
        print("TIME BOX HIT")
        break
    fn = os.path.basename(path)
    try:
        env = UnityPy.load(path)
    except Exception as e:
        print("  skip", fn, "load err", e); continue
    # iterate container mapping (cheap: just names)
    found_here = []
    try:
        cont = env.container  # dict path->obj
    except Exception:
        cont = {}
    for cpath in cont.keys():
        low = cpath.lower()
        if "music033" in low or "sounds01/bgm_/music033" in low:
            found_here.append(cpath)
    if found_here:
        print(f"\n=== {fn} ===")
        for cpath in found_here:
            obj = cont[cpath]
            data = obj.read()
            name = getattr(data, "m_Name", getattr(data, "name", "?"))
            # size of the TextAsset script bytes
            script = getattr(data, "m_Script", None) or getattr(data, "script", None)
            blen = len(script) if script is not None else "?"
            print(f"  container: {cpath}")
            print(f"    type={obj.type.name} name={name!r} bytes_len={blen}")
            hits.append((fn, cpath, obj.type.name, str(name), blen))
print("\n--- SUMMARY ---")
for h in hits:
    print(h)
if not hits:
    print("music033 NOT found in any container-keyed bundle (may be name-only asset)")
