"""GAP lens: verify Unity BuildSettings scene order (boot-scene chain) from mainData.
Read-only. Prints the ordered scene list (index = Application.LoadLevel index).
Usage: py gap_buildsettings_probe.py
"""
import UnityPy, re

MAIN = r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX\x64\FF9_Data\mainData"

def main():
    env = UnityPy.load(MAIN)
    found = False
    for obj in env.objects:
        if "BuildSettings" in str(obj.type):
            found = True
            try:
                d = obj.read_typetree()
            except Exception as e:
                print("typetree err:", e); d = None
            if d:
                for k in d:
                    if k.lower() == "scenes":
                        print("=== BuildSettings.scenes (LoadLevel index order) ===")
                        for i, s in enumerate(d[k]):
                            print(f"  [{i}] {s}")
                    else:
                        print(f"  {k} = {d[k]}")
    if not found:
        print("No BuildSettings typetree object; brute-scanning byte offsets of scene names...")
        data = open(MAIN, "rb").read()
        hits = []
        for name in [b"BundleSceneSelector", b"SplashScreen", b"Bundle", b"MainMenu",
                     b"Title", b"FieldMap", b"WorldMap", b"BattleMap"]:
            idxs = [m.start() for m in re.finditer(re.escape(name), data)]
            if idxs:
                hits.append((idxs[0], name.decode()))
            print(f"  {name.decode():20s} count={len(idxs)} first_off={idxs[0] if idxs else '-'}")
        print("--- by first byte offset (approx build order) ---")
        for off, n in sorted(hits):
            print(f"  {off:>10}  {n}")

if __name__ == "__main__":
    main()
