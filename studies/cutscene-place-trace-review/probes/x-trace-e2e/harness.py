"""Shared harness: a TraceDoc with a REAL run seam (the CLI executes), driven by real Qt events."""
import os, sys, subprocess, tempfile, json, shutil
from pathlib import Path

HERE = Path(__file__).parent
_PREFS = Path(tempfile.mkdtemp(prefix="xtrace_prefs_", dir=HERE))
os.environ["LOCALAPPDATA"] = str(_PREFS)             # never the developer's real prefs
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
KIT = Path(r"C:/gd/Dream-World-IX/.claude/worktrees/inspiring-wing-600ac9/ff9mapkit")
sys.path.insert(0, str(KIT))

from PySide6.QtCore import Qt, QPoint, QPointF                       # noqa: E402
from PySide6.QtGui import QContextMenuEvent                          # noqa: E402
from PySide6.QtTest import QTest                                     # noqa: E402
from PySide6.QtWidgets import QApplication, QMenu                    # noqa: E402

app = QApplication.instance() or QApplication([])
import ff9mapkit                                                      # noqa: E402
assert str(Path(ff9mapkit.__file__)).lower().startswith(str(KIT).lower()), ff9mapkit.__file__
from ff9mapkit.workspace.shell import pick_palette                   # noqa: E402
from ff9mapkit.workspace.tracedoc import TraceDoc                    # noqa: E402
from ff9mapkit import imagefield as IF                               # noqa: E402

# the child env a Workspace QProcess inherits (no UTF-8 forcing unless the user set it)
CHILD_ENV = {k: v for k, v in os.environ.items() if k not in ("PYTHONIOENCODING", "PYTHONUTF8")}


class RealRun:
    """The run_job seam, EXECUTED: the argv runs for real; on_finished fires AFTER on_generate
    returns (QProcess is async), via flush()."""
    def __init__(self, env=None):
        self.calls, self.pending, self.env = [], [], env or CHILD_ENV

    def __call__(self, argv, *, cwd=None, on_finished=None, **kw):
        r = subprocess.run([str(a) for a in argv], cwd=cwd, capture_output=True, env=self.env)
        out = (r.stdout + r.stderr).decode("cp1252", "replace")
        self.calls.append({"argv": list(argv), "code": r.returncode, "out": out, "kw": kw})
        self.pending.append((on_finished, r.returncode))
        return True

    def flush(self):
        p, self.pending = self.pending, []
        for cb, code in p:
            if cb:
                cb(code)


def make_doc(env=None, size=(1400, 1000)):
    run = RealRun(env)
    handed = []
    doc = TraceDoc(pick_palette("dark"), KIT, run=run, on_generated=handed.append)
    doc.resize(*size)
    doc.show()
    for _ in range(5):
        app.processEvents()
    doc.canvas._fit()
    app.processEvents()
    return doc, run, handed


def vp_pos(doc, cx, cy):
    p = doc.canvas.mapFromScene(QPointF(cx, cy))
    return QPoint(p.x(), p.y())


def click(doc, cx, cy, button=Qt.MouseButton.LeftButton):
    vp = doc.canvas.viewport()
    pos = vp_pos(doc, cx, cy)
    QTest.mousePress(vp, button, Qt.KeyboardModifier.NoModifier, pos)
    QTest.mouseRelease(vp, button, Qt.KeyboardModifier.NoModifier, pos)
    app.processEvents()


def drag(doc, a, b, steps=6):
    vp = doc.canvas.viewport()
    pa, pb = vp_pos(doc, *a), vp_pos(doc, *b)
    QTest.mousePress(vp, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, pa)
    for k in range(1, steps + 1):
        p = QPoint(pa.x() + (pb.x() - pa.x()) * k // steps, pa.y() + (pb.y() - pa.y()) * k // steps)
        QTest.mouseMove(vp, p)
        app.processEvents()
    QTest.mouseRelease(vp, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, pb)
    app.processEvents()


def context(doc, cx, cy, choose):
    """Right-click at canvas px; the popup's exec is patched to pick the action whose text
    starts with ``choose``."""
    import PySide6.QtWidgets as QW
    orig = QW.QMenu
    picked = []

    class FakeMenu(orig):
        def exec(self, *a, **k):
            for act in self.actions():
                if act.text().startswith(choose):
                    picked.append(act.text())
                    return act
            picked.append(None)
            return None
    QW.QMenu = FakeMenu
    try:
        vp = doc.canvas.viewport()
        pos = vp_pos(doc, cx, cy)
        ev = QContextMenuEvent(QContextMenuEvent.Reason.Mouse, pos, vp.mapToGlobal(pos))
        QApplication.sendEvent(vp, ev)
        app.processEvents()
    finally:
        QW.QMenu = orig
    return picked


def room(path, size=(800, 600)):
    from PIL import Image, ImageDraw
    w, h = size
    img = Image.new("RGB", size, (38, 42, 58))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, w, int(h * .31)], fill=(52, 56, 76))
    d.polygon([(w * .34, h * .31), (w * .66, h * .31), (w * .95, h * .98), (w * .05, h * .98)],
              fill=(158, 132, 96))
    img.save(path)
    return Path(path)


def snip(path, size=(120, 200)):
    from PIL import Image
    im = Image.new("RGBA", size, (0, 0, 0, 0))
    for x in range(20, size[0] - 20):
        for y in range(0, size[1]):
            im.putpixel((x, y), (150, 150, 160, 255))
    im.save(path)
    return Path(path)


def files_snapshot(folder):
    import hashlib
    out = {}
    for p in sorted(Path(folder).rglob("*")):
        if p.is_file():
            out[str(p.relative_to(folder)).replace("\\", "/")] = hashlib.sha1(p.read_bytes()).hexdigest()[:10]
    return out
