import os, UnityPy
DATA = r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX\x64\FF9_Data"

# level6 = Title.unity : dump ALL GameObject names
e = UnityPy.load(os.path.join(DATA, "level6"))
gos = []
for obj in e.objects:
    if obj.type.name == "GameObject":
        try:
            gos.append(obj.read().m_Name)
        except Exception:
            pass
print("level6 GameObjects (%d):" % len(gos), sorted(gos))

# scripts present in level6
scripts = set()
for obj in e.objects:
    if obj.type.name == "MonoBehaviour":
        try:
            d = obj.read(); sc = getattr(d, "m_Script", None)
            if sc: scripts.add(getattr(sc.read(), "m_ClassName", ""))
        except Exception: pass
print("level6 MonoBehaviour scripts:", sorted(s for s in scripts if s))

# splash_image Sprite in resources.assets?
r = UnityPy.load(os.path.join(DATA, "resources.assets"))
found = {"Sprite": [], "Texture2D": []}
for obj in r.objects:
    if obj.type.name in ("Sprite", "Texture2D"):
        try:
            d = obj.read()
            if getattr(d, "m_Name", "") == "splash_image":
                if obj.type.name == "Texture2D":
                    found["Texture2D"].append("%dx%d" % (d.m_Width, d.m_Height))
                else:
                    found["Sprite"].append(str(obj.path_id))
        except Exception: pass
print("splash_image Texture2D dims:", found["Texture2D"])
print("splash_image Sprite path_ids:", found["Sprite"])
