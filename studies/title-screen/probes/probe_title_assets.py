"""Inventory FF9 title-screen assets in the regular Unity assets files.
Scans resources.assets + sharedassets0/1.assets + mainData for containers/objects
matching title-related keywords. READ-ONLY. Time-boxed via keyword filter.

Run: py probe_title_assets.py
"""
import os, sys, time
import UnityPy

DATA = r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX\x64\FF9_Data"
FILES = ["resources.assets", "sharedassets0.assets", "sharedassets1.assets", "mainData"]
KW = ["title", "logo", "splash", "caution", "warning", "sqex", "silicon", "square", "enix"]

def matches(s):
    if not s: return False
    s = s.lower()
    return any(k in s for k in KW)

for fn in FILES:
    path = os.path.join(DATA, fn)
    if not os.path.exists(path):
        print(f"### {fn}: MISSING"); continue
    t0 = time.time()
    print(f"\n############ {fn} ({os.path.getsize(path)/1e6:.1f} MB) ############")
    env = UnityPy.load(path)

    # --- 1) container-path matches (this is how Resources.Load resolves) ---
    print("---- container keys matching keywords ----")
    ccount = 0
    try:
        for cpath, obj in env.container.items():
            if matches(cpath):
                ccount += 1
                try:
                    typ = obj.type.name
                except Exception:
                    typ = "?"
                extra = ""
                try:
                    if typ in ("Texture2D", "Sprite"):
                        d = obj.read()
                        w = getattr(d, "m_Width", getattr(d, "width", "?"))
                        h = getattr(d, "m_Height", getattr(d, "height", "?"))
                        extra = f" [{w}x{h}] name={getattr(d,'m_Name',getattr(d,'name','?'))}"
                    elif typ == "AudioClip":
                        d = obj.read()
                        extra = f" name={getattr(d,'m_Name','?')}"
                except Exception as e:
                    extra = f" <read-fail {e}>"
                print(f"  {typ:12} :: {cpath}{extra}")
        print(f"  ({ccount} container matches; container size={len(env.container)})")
    except Exception as e:
        print(f"  container iter failed: {e}")

    # --- 2) object m_Name matches for texture/sprite/audio/text ---
    print("---- object m_Name matches (Texture2D/Sprite/AudioClip/TextAsset/Material) ----")
    ocount = 0
    WANT = {"Texture2D", "Sprite", "AudioClip", "TextAsset", "Material"}
    for obj in env.objects:
        try:
            tn = obj.type.name
        except Exception:
            continue
        if tn not in WANT:
            continue
        try:
            d = obj.read()
        except Exception:
            continue
        nm = getattr(d, "m_Name", getattr(d, "name", ""))
        if matches(nm):
            ocount += 1
            extra = ""
            if tn in ("Texture2D", "Sprite"):
                w = getattr(d, "m_Width", getattr(d, "width", "?"))
                h = getattr(d, "m_Height", getattr(d, "height", "?"))
                extra = f" [{w}x{h}]"
            print(f"  {tn:12} :: {nm}{extra} (pathid={obj.path_id})")
        if ocount > 200:
            print("  ...(capped)"); break
    print(f"  ({ocount} object-name matches; elapsed {time.time()-t0:.1f}s)")
