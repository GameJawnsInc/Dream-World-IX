import sys, time, shutil, tomllib; sys.path.insert(0, r"<SCRATCH>/review/x-cutscene-place")
import h, faulthandler
faulthandler.dump_traceback_later(60, exit=True)
from PySide6.QtCore import Qt, QPoint, QPointF, QEvent
from PySide6.QtGui import QContextMenuEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QMenu
from ff9mapkit import floorplan as FP
from ff9mapkit.workspace import placedoc as PD

root = h.OUT / "work" / "novel"
shutil.rmtree(root, ignore_errors=True); root.mkdir(parents=True)
plan = {"name": "D", "mod_folder": "FF9CustomMap", "id_base": 30700, "entry": "A",
        "rooms": [{"name": "A", "poly": [[0, 0], [2400, 0], [2400, 1800], [0, 1800]]}], "doors": []}
FP.compose_and_emit(plan, root, log=None)
toml = next((root / "A").glob("*.field.toml"))
print("novel toml", toml.name)

MENU = {"pick": None}
def menu_exec(menu, *a, **k):
    acts = [a_.text() for a_ in menu.actions()]
    print("   [menu]", acts, "->", MENU["pick"])
    for a_ in menu.actions():
        if MENU["pick"] and a_.text().startswith(MENU["pick"]):
            return a_
    return None
import PySide6.QtWidgets as _QW
class _M(QMenu):
    def exec(self, *a, **k):
        return menu_exec(self)
_QW.QMenu = _M

def wait_load(pd, cap=30):
    t = time.time()
    while pd._loading is not None and time.time() - t < cap:
        h.settle(1); time.sleep(0.03)
    h.settle(3)

with h.gs._no_modals():
    c = h.ctx()
    win = h.gs._make_win(c)
    assert win.open_field(toml)
    member = next(iter(win._docs))
    pd = win.place_doc
    win.tabs.setCurrentWidget(pd); h.settle(4)
    print("member", member, "status:", pd.status.text()[:100])
    pd.load_btn.click(); wait_load(pd)
    print("loaded:", pd._bundle() is not None, "status:", pd.status.text()[:100])
    cv = pd.canvas; vp = cv.viewport()
    data = lambda: win._docs[member].data
    def click_world(x, z, btn=Qt.MouseButton.LeftButton):
        p = cv.world_to_click((x, z)).toPoint()
        QTest.mouseClick(vp, btn, Qt.KeyboardModifier.NoModifier, p); h.settle(3)
        return p
    # find a floor centre from the surface tris
    xs = [v[0] for t in pd._bundle()["tris"] for v in t]; zs = [v[2] for t in pd._bundle()["tris"] for v in t]
    cx, cz = (min(xs) + max(xs)) / 2, (min(zs) + max(zs)) / 2
    print("floor extent x", min(xs), max(xs), "z", min(zs), max(zs))
    # ---- arrival + spawn + undo/redo
    pd.mode_btns["arrival"].setChecked(True); h.settle(1)
    print("ent visible", pd.ent_box.isVisible()); pd.ent_box.setValue(2)
    click_world(cx, cz)
    print("after arrival:", data().get("player"), "| status", pd.status.text())
    pd.mode_btns["spawn"].setChecked(True); h.settle(1)
    click_world(cx + 300, cz)
    print("after spawn:", data().get("player"))
    pd.mode_btns["arrival"].setChecked(True); pd.ent_box.setValue(2); click_world(cx - 300, cz)
    print("arrival 2 moved:", data().get("player"))
    n0 = len(win._undo_stack)
    win._undo(); h.settle(3); print("undo1:", data().get("player"), "tab is place", win.tabs.currentWidget() is pd, "markers", len(cv._markers) if hasattr(cv, "_markers") else "?")
    win._undo(); h.settle(3); print("undo2:", data().get("player"))
    win._redo(); h.settle(3); print("redo:", data().get("player"))
    win._redo(); h.settle(3); print("redo2:", data().get("player"))
    print("mode after history:", pd._mode(), "ent", pd.ent_box.value(), "ent visible", pd.ent_box.isVisible())
    # ---- save + reopen
    win._save_all(); h.settle(3)
    disk = tomllib.loads(toml.read_text(encoding="utf-8"))
    print("disk player:", disk.get("player"))
    print("disk == buffer (player):", disk.get("player") == data().get("player"))
    # ---- regions
    pd.tools.set_current("regions"); h.settle(2)
    pd.gw_to.setValue(0)
    U0 = len(win._undo_stack)
    q = [(cx - 400, cz - 300), (cx + 100, cz - 300), (cx + 100, cz + 300), (cx - 400, cz + 300)]
    for x, z in q:
        click_world(x, z)
    print("gateway drawn:", data().get("gateway"), "undo+", len(win._undo_stack) - U0)
    # retarget via a REAL context menu on the quad body
    pd._ask_field_id = lambda cur: 4005
    def ctx_at(x, z):
        p = cv.world_to_click((x, z)).toPoint()
        ev = QContextMenuEvent(QContextMenuEvent.Reason.Mouse, p, vp.mapToGlobal(p))
        h.app.sendEvent(vp, ev); h.settle(3)
    MENU["pick"] = "Set gateway target"; ctx_at(cx - 150, cz)
    print("retarget:", data()["gateway"][0]["to"], "undo+", len(win._undo_stack) - U0)
    MENU["pick"] = "Walk-out edge"; ctx_at(cx - 150, cz)
    print("rotate:", data()["gateway"][0]["zone"], "undo+", len(win._undo_stack) - U0)
    # corner drag (corner 2)
    z2 = data()["gateway"][0]["zone"][2]
    p = cv.world_to_click((z2[0], z2[1])).toPoint()
    QTest.mousePress(vp, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, p)
    for k in range(1, 6): QTest.mouseMove(vp, p + QPoint(6 * k, 3 * k)); h.settle(1)
    QTest.mouseRelease(vp, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, p + QPoint(30, 15)); h.settle(3)
    print("corner drag:", data()["gateway"][0]["zone"], "undo+", len(win._undo_stack) - U0)
    # body drag
    p = cv.world_to_click((cx - 150, cz)).toPoint()
    QTest.mousePress(vp, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, p)
    for k in range(1, 6): QTest.mouseMove(vp, p + QPoint(-5 * k, 0)); h.settle(1)
    QTest.mouseRelease(vp, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, p + QPoint(-25, 0)); h.settle(3)
    print("body drag:", data()["gateway"][0]["zone"], "undo+", len(win._undo_stack) - U0)
    labels = [r.label for r in win._undo_stack[U0:]]
    print("undo labels:", labels)
    for _ in range(4):
        win._undo(); h.settle(3)
        g = data().get("gateway") or [{}]
        print("  undo ->", g[0].get("to"), g[0].get("zone"), "| tool", pd.tools.current(), "regions on canvas", len(pd._region_rows_cache))
    # event + message + delete
    for _ in range(4): win._redo(); h.settle(2)
    pd.rkind_btns["event"].setChecked(True); h.settle(1)
    q2 = [(cx + 300, cz - 200), (cx + 700, cz - 200), (cx + 700, cz + 200), (cx + 300, cz + 200)]
    for x, z in q2: click_world(x, z)
    pd._ask_message = lambda cur: "Hello there"
    MENU["pick"] = "Set message"; ctx_at(cx + 500, cz)
    print("event:", data().get("event"))
    MENU["pick"] = "Delete"; ctx_at(cx + 500, cz)
    print("event after delete:", data().get("event"))
    win._undo(); h.settle(3); print("undo delete:", data().get("event"))
    print("status:", pd.status.text())
    h.gs._close(win)
