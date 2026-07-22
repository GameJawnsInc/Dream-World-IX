"""Read BuildSettings scene list (name->build index) from mainData.
READ-ONLY. Maps scene names like 'SplashScreen'/'Title'/'FieldMap' to level index."""
import UnityPy, re
DATA = r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX\x64\FF9_Data"
for fn in ["mainData", "globalgamemanagers"]:
    p = DATA + "\\" + fn
    try:
        env = UnityPy.load(p)
    except Exception as e:
        print(fn, "load err", e); continue
    print("="*60, "\nFILE:", fn)
    for obj in env.objects:
        if obj.type.name == "BuildSettings":
            try:
                d = obj.read_typetree()
                scenes = d.get("scenes", [])
                print("  BuildSettings.scenes (index -> path):")
                for i, s in enumerate(scenes):
                    print(f"    [{i}] {s}")
            except Exception as e:
                print("  BuildSettings read err:", e)
    # also dump PlayerSettings? skip.
