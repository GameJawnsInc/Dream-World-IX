"""THE APP-SHEET GUARD: no test sets a stylesheet on the QApplication.

``QApplication.setStyleSheet`` repolishes EVERY widget alive in the process, and does it again on the restore.
An xdist worker keeps thousands of widgets alive by design (``tests/conftest.py``'s ``qt_drain`` PARKS widget
graphs, so shiboken never finalizes them under GC). So one app-wide sheet costs whatever ran earlier in that
worker. Measured on the 2026-11-03 nightly: two Info Hub fences that take 0.22 s / 0.14 s alone took
878 s / 740 s there, ~27 worker-minutes a night.

It is not where the app puts its sheet, either. The Workspace calls ``self.setStyleSheet(qss(...))`` on its OWN
window (``shell.py``) and parents its dialogs to it (``CatalogLibrary(self, ...)``). So a fence that needs the
app sheet builds a host widget carrying ``style.qss(...)`` and parents its subject to it: the same cascade the
app runs, polishing only the subject's own tree (``test_workspace_a11y``'s id-button host,
``test_workspace_encounters._app_sheet_host``).

The scan is static: every test module the gate collects is read, and each one that names ``setStyleSheet`` is
parsed and walked. It takes well under a second and also reads code that never runs in this worker. The
receivers it knows: ``QApplication.instance()`` / ``QApplication(...)`` / ``qApp`` written inline, any name
bound to one of those (or to another such name), and an ``app`` / ``qapp`` parameter (every such fixture in
these trees returns the QApplication). A restore to ``""`` is allowed: it is a no-op when nothing set a sheet,
and the set it would undo is already a finding.
"""
from __future__ import annotations

import ast
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]                 # ff9mapkit/ (holds tests/ and blender/tests/)
TREES = (KIT / "tests", KIT / "blender" / "tests", KIT.parent / "docsite" / "tests")
_APP_CLASSES = {"QApplication", "QGuiApplication", "QCoreApplication"}
_APP_PARAMS = {"app", "qapp"}


def _is_app_class(node) -> bool:
    """``QApplication`` or a dotted ``QtWidgets.QApplication``."""
    return ((isinstance(node, ast.Name) and node.id in _APP_CLASSES)
            or (isinstance(node, ast.Attribute) and node.attr in _APP_CLASSES))


def _is_app(node, bound: set[str]) -> bool:
    """Does this expression evaluate to the QApplication?"""
    if isinstance(node, ast.Call):
        f = node.func
        if isinstance(f, ast.Attribute) and f.attr == "instance" and _is_app_class(f.value):
            return True                                   # QApplication.instance()
        return _is_app_class(f)                           # QApplication([])
    if isinstance(node, ast.BoolOp):                      # QApplication.instance() or QApplication([])
        return any(_is_app(v, bound) for v in node.values)
    if isinstance(node, ast.Name):
        return node.id == "qApp" or node.id in bound
    return False


def _bound_app_names(tree) -> set[str]:
    """Every name the module binds to the QApplication. Module-wide on purpose (a name bound in one function and
    reused in another is caught), and run to a fixpoint so ``inst = app`` follows ``app``."""
    nodes = list(ast.walk(tree))
    bound = {a.arg for n in nodes if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
             for a in n.args.args + n.args.kwonlyargs if a.arg in _APP_PARAMS}
    binds = [(t.id, n.value) for n in nodes if isinstance(n, (ast.Assign, ast.AnnAssign)) and n.value is not None
             for t in (n.targets if isinstance(n, ast.Assign) else [n.target]) if isinstance(t, ast.Name)]
    while True:
        more = {name for name, value in binds if name not in bound and _is_app(value, bound)}
        if not more:
            return bound
        bound |= more


def app_sheet_calls(source: str) -> list[int]:
    """Line numbers of every ``<the QApplication>.setStyleSheet(<anything but "">)`` in ``source``."""
    tree = ast.parse(source)
    bound = _bound_app_names(tree)
    hits = []
    for n in ast.walk(tree):
        if not (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "setStyleSheet"):
            continue
        if not _is_app(n.func.value, bound):
            continue
        arg = n.args[0] if n.args else None
        if isinstance(arg, ast.Constant) and arg.value == "":
            continue                                      # the restore: a no-op unless a set preceded it
        hits.append(n.lineno)
    return sorted(hits)


def test_the_scan_catches_every_receiver_shape_and_spares_a_host():
    """THE POSITIVE CONTROL: a scan that cannot fail guards nothing. Each shape below once reached, or could
    reach, the app; the host and the restore must not be flagged."""
    caught = {
        "inline": "def t():\n    QApplication.instance().setStyleSheet(qss)\n",
        "bound": "def t():\n    inst = QApplication.instance()\n    inst.setStyleSheet(qss)\n",
        "fixture": "def t(app):\n    app.setStyleSheet(qss)\n",
        "alias": "def t(app):\n    a = app\n    a.setStyleSheet(qss)\n",
        "or-new": "def t():\n    q = QApplication.instance() or QApplication([])\n    q.setStyleSheet(qss)\n",
        "dotted": "def t():\n    QtWidgets.QApplication.instance().setStyleSheet(qss)\n",
        "qApp": "def t():\n    qApp.setStyleSheet(qss)\n",
        "module": "APP = QApplication.instance()\ndef t():\n    APP.setStyleSheet(qss)\n",
    }
    for shape, src in caught.items():
        assert app_sheet_calls(src), f"the scan missed the {shape!r} shape"
    spared = {
        "host": "def t(app):\n    host = QWidget()\n    host.setStyleSheet(qss)\n",
        "restore": "def t(app):\n    app.setStyleSheet('')\n",
        "widget": "def t():\n    w = QPushButton()\n    w.setStyleSheet('color: red')\n",
    }
    for shape, src in spared.items():
        assert not app_sheet_calls(src), f"the scan flagged the harmless {shape!r} shape"


def test_no_test_sets_a_stylesheet_on_the_qapplication():
    files = [p for root in TREES if root.is_dir() for p in sorted(root.rglob("test_*.py"))]
    assert len(files) > 100, f"the scan found only {len(files)} test modules -- it is reading the wrong trees"
    offenders = []
    for p in files:
        src = p.read_text(encoding="utf-8")
        if "setStyleSheet" in src:                        # the trees hold ~16 MB: parse only what can call it
            offenders += [f"{p.relative_to(KIT.parent)}:{line}" for line in app_sheet_calls(src)]
    assert not offenders, (
        "a test sets a stylesheet on the QApplication, which repolishes every widget alive in the xdist "
        "worker (878 s for a 0.22 s test, 2026-11-03). Put the sheet on a host widget and parent the "
        "subject to it, the way the Workspace does: " + ", ".join(offenders))
