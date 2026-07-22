import UnityPy, os
base = r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX\x64\FF9_Data"
for idx,label in [(4,"MainMenu"),(6,"Title"),(0,"BundleSceneSelector"),(2,"Bundle")]:
    path = os.path.join(base, f"level{idx}")
    print(f"\n==== level{idx} = {label} scene ====")
    try:
        env = UnityPy.load(path)
        names=set()
        for obj in env.objects:
            if obj.type.name in ("MonoBehaviour","GameObject","MonoScript"):
                try:
                    d = obj.read()
                    # try to get script class name
                    cn = getattr(d,"m_ClassName",None) or getattr(d,"name",None)
                    if obj.type.name=="MonoBehaviour":
                        # resolve script
                        try:
                            script = d.m_Script.read()
                            names.add(("MB->", script.m_ClassName))
                        except Exception as e:
                            names.add(("MB(name)", getattr(d,"name","?")))
                    elif obj.type.name=="MonoScript":
                        names.add(("Script", d.m_ClassName))
                    elif obj.type.name=="GameObject":
                        names.add(("GO", d.name))
                except Exception as e:
                    pass
        for t in sorted(names, key=lambda x:(x[0],str(x[1]))):
            print("  ",t[0], t[1])
    except Exception as e:
        print("  ERROR", e)
