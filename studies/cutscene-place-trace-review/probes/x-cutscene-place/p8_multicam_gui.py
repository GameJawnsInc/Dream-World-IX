import sys, time, faulthandler; sys.path.insert(0, r"<SCRATCH>/review/x-cutscene-place")
faulthandler.dump_traceback_later(80, exit=True)
import h
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

def wait_load(pd, cap=30):
    t = time.time()
    while pd._loading is not None and time.time() - t < cap:
        h.settle(1); time.sleep(0.03)
    h.settle(3)

toml = h.OUT / "work" / "multicam_auto" / "a.field.toml"
with h.gs._no_modals():
    win = h.gs._make_win(h.ctx())
    assert win.open_field(toml)
    m = next(iter(win._docs))
    pd = win.place_doc; win.tabs.setCurrentWidget(pd); h.settle(3)
    pd.load_btn.click(); wait_load(pd)
    print("cam box visible", pd.cam_box.isVisible(), "items", pd.cam_box.count(), "status", pd.status.text()[:80])
    cv = pd.canvas; vp = cv.viewport()
    pd.cam_box.setCurrentIndex(1); wait_load(pd)
    print("cam 1 loaded:", pd._bundle() is not None, "cam idx", pd._cam_index(), "markers", len(cv._markers))
    # click a point that is ON camera 1's framed floor but OFF the shipped (cam-0-framed) floor: z=300
    p = cv.world_to_click((0, 300)).toPoint()
    pd.mode_btns["npc"].setChecked(True)
    QTest.mouseClick(vp, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, p); h.settle(3)
    print("click z=300 under cam 1:", pd.status.text(), "| npcs", win._docs[m].data.get("npc"))
    pd.cam_box.setCurrentIndex(0); wait_load(pd)
    print("back on cam 0 markers", len(cv._markers), "status", pd.status.text()[:90])
    # build-side verdict on that NPC
    from ff9mapkit import build
    proj = build.FieldProject.load(str(toml)); proj.raw.update(win._docs[m].data)
    from ff9mapkit.scene import bgi
    wm = bgi.BgiWalkmesh.from_bytes(build.resolve_walkmesh(proj, build.resolve_camera(proj)))
    warns = []
    try:
        build._validate_content_placement(proj, wm, warns)
    except Exception as e:
        warns.append(f"EXC {e}")
    print("build placement warnings:", [w for w in warns if "npc" in str(w).lower() or "walkmesh" in str(w).lower()][:3])
    h.gs._close(win)
