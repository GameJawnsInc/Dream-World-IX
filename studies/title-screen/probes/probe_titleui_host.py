"""Confirm the GameObject hosting the TitleUI MonoBehaviour in level1 by matching
m_Script PPtr -> (external file, path_id 307 in sharedassets0). READ-ONLY."""
import UnityPy, os
DATA = r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX\x64\FF9_Data"
env = UnityPy.load(DATA + r"\level1")
sf = list(env.files.values())[0]
ext = [os.path.basename(getattr(e,"path","") or "") for e in sf.externals]
print("level1 externals (file_id order): [0]=<self>", *[f"[{i+1}]={n}" for i,n in enumerate(ext)])
# TitleUI MonoScript = sharedassets0.assets path_id 307 ; UIManager = 407
SA0 = None
for i,n in enumerate(ext):
    if n.lower()=="sharedassets0.assets": SA0=i+1
print("sharedassets0 file_id =", SA0)

go_name={}
for obj in env.objects:
    if obj.type.name=="GameObject":
        try: go_name[obj.path_id]=obj.read().m_Name
        except: pass

TARGETS={307:"TitleUI",407:"UIManager"}
print("\nMonoBehaviours whose m_Script -> sharedassets0 path_id in",list(TARGETS)," :")
for obj in env.objects:
    if obj.type.name!="MonoBehaviour": continue
    try:
        d=obj.read_typetree()
        scr=d.get("m_Script",{})
        fid=scr.get("m_FileID"); pid=scr.get("m_PathID")
        if fid==SA0 and pid in TARGETS:
            gpid=d.get("m_GameObject",{}).get("m_PathID",0)
            print(f"   {TARGETS[pid]}: MB path_id={obj.path_id} on GO='{go_name.get(gpid,'?')}' (go={gpid}) [m_Script fid={fid} pid={pid}]")
    except Exception as e:
        pass
