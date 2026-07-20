"""Confirm TitleUI/UIManager host GO via generic read() PPtr attrs. READ-ONLY."""
import UnityPy, os
DATA = r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX\x64\FF9_Data"
env = UnityPy.load(DATA + r"\level1")
sf = list(env.files.values())[0]
ext = [os.path.basename(getattr(e,"path","") or "") for e in sf.externals]
SA0 = next((i+1 for i,n in enumerate(ext) if n.lower()=="sharedassets0.assets"), None)
go_name={}
for obj in env.objects:
    if obj.type.name=="GameObject":
        try: go_name[obj.path_id]=obj.read().m_Name
        except: pass
TARGETS={307:"TitleUI",407:"UIManager"}
ok=0; err=0; hits=0
for obj in env.objects:
    if obj.type.name!="MonoBehaviour": continue
    try:
        mb=obj.read()
        scr=getattr(mb,"m_Script",None)
        if scr is None: err+=1; continue
        fid=getattr(scr,"m_FileID",getattr(scr,"file_id",None))
        pid=getattr(scr,"m_PathID",getattr(scr,"path_id",None))
        ok+=1
        if fid==SA0 and pid in TARGETS:
            go=getattr(mb,"m_GameObject",None)
            gpid=getattr(go,"m_PathID",getattr(go,"path_id",None)) if go else None
            print(f"   {TARGETS[pid]}: MB={obj.path_id} on GO='{go_name.get(gpid,'?')}' (go={gpid}) [fid={fid} pid={pid}]")
            hits+=1
    except Exception as e:
        err+=1
print(f"\nMBs with readable m_Script PPtr: {ok}, errors: {err}, target hits: {hits}")
