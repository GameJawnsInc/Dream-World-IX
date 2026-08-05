"""THE FREE-NAME CAPTURE GUARD: no diagnostic may format a module-level FUNCTION or MODULE.

THE DEFECT THIS EXISTS TO MAKE UNSHIPPABLE. ``content/behavior.py`` imports ``eb.labelasm.label``
(behavior.py:59) and also uses ``label`` as the name of the *diagnostic prefix* parameter that lets a
second lane reuse ``hud_expr_tokens``. A find/replace that parameterised that prefix overshot out of
``hud_expr_tokens`` into ``FieldBehavior._hud_ref``, which has NO ``label`` parameter -- so Python
resolved the free name to the MODULE-GLOBAL function and four shipped ``[[behavior.hud]]`` refusals
rendered ``<function label at 0x000002BB1E0503B0> 'hp:ghost': unknown unit 'ghost'``. No NameError, no
test failure: ``tests/test_behavior.py`` matched the substring ``unknown unit``, which the corrupted
prefix leaves intact. The only thing standing between that and an unhandled NameError *inside a
refusal path* was that a function of that name happened to be in scope.

THE RULE. Inside a function body, an f-string may not interpolate a BARE name that (a) no enclosing
function scope binds and (b) the module binds to a ``def``/``class``/``import``. Formatting a
module-level CONSTANT (``f"{FIRST_SAFE_FLAG}"``) is ordinary and stays legal -- the scan resolves each
from-import one hop into the package to tell the two apart, and declines to flag anything it cannot
resolve. This is a whole-package scan, so it covers every lane that has not been written yet.

Pure source parsing: no imports of the modules under test, no game data, no install -- it runs
identically in a fresh worktree.
"""

from __future__ import annotations

import ast
import builtins
import pathlib

PKG = pathlib.Path(__file__).resolve().parent.parent / "ff9mapkit"

#: how many from-import hops to follow before giving up and NOT flagging
_MAX_HOPS = 3


def _parse(path: pathlib.Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _module_bindings(tree: ast.Module) -> dict:
    """name -> ("callable"|"module"|"data", None) or ("from", (level, module, orig_name))."""
    out = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            out[node.name] = ("callable", None)
        elif isinstance(node, ast.Import):
            for a in node.names:
                out[a.asname or a.name.split(".")[0]] = ("module", None)
        elif isinstance(node, ast.ImportFrom):
            for a in node.names:
                out[a.asname or a.name] = ("from", (node.level, node.module or "", a.name))
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            kind = "callable" if isinstance(node.value, ast.Lambda) else "data"
            for t in targets:
                if isinstance(t, ast.Name):
                    out[t.id] = (kind, None)
    return out


def _resolve_module(src: pathlib.Path, level: int, module: str):
    """The .py file a ``from ... import`` names, or None when it leaves the package."""
    if level:                                             # relative: walk up from THIS file's package
        base = src.parent
        for _ in range(level - 1):
            base = base.parent
    elif module.split(".")[0] == PKG.name:
        base = PKG.parent
    else:
        return None                                       # stdlib / third-party: not ours to classify
    cand = base.joinpath(*module.split(".")) if module else base
    for p in (cand.with_suffix(".py"), cand / "__init__.py"):
        if p.is_file():
            return p
    return None


def _classify(src: pathlib.Path, name: str, hops: int = 0) -> str:
    """What KIND of object a module-level name is bound to. "unknown" is never flagged."""
    if hops > _MAX_HOPS or not src.is_file():
        return "unknown"
    kind, extra = _module_bindings(_parse(src)).get(name, (None, None))
    if kind is None:
        return "unknown"                                  # star-import, conditional binding, ...
    if kind != "from":
        return kind
    level, module, orig = extra
    nxt = _resolve_module(src, level, module)
    if nxt is None:
        return "unknown"
    if nxt.name == "__init__.py" and (nxt.parent / f"{orig}.py").is_file():
        return "module"                                   # `from .pkg import submodule`
    return _classify(nxt, orig, hops + 1)


def _binds(fn) -> set:
    """Every name this function binds itself -- params, assignments, imports, except-as, ..."""
    out = set()
    a = fn.args
    for arg in list(a.posonlyargs) + list(a.args) + list(a.kwonlyargs):
        out.add(arg.arg)
    if a.vararg:
        out.add(a.vararg.arg)
    if a.kwarg:
        out.add(a.kwarg.arg)

    def rec(node, top=False):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and not top:
            out.add(node.name)                            # the nested def's NAME binds here...
            return                                        # ...its body does not
        if isinstance(node, ast.Lambda) and not top:
            return
        if isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
            out.add(node.id)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for al in node.names:
                out.add(al.asname or al.name.split(".")[0])
        elif isinstance(node, (ast.Global, ast.Nonlocal)):
            out.update(node.names)
        elif isinstance(node, ast.ExceptHandler) and node.name:
            out.add(node.name)
        for sub in ast.iter_child_nodes(node):
            rec(sub)

    rec(fn, top=True)
    return out


_NESTED = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)


def _fstring_names(node) -> list:
    """(name, lineno) for every f-string hole in THIS scope that formats a BARE name.

    A call / attribute / subscript hole is a deliberate expression and is left alone, and the descent
    STOPS at a nested def or lambda -- that body has its own, wider scope, and attributing its holes
    here would report a parameter of the inner function as a module-level capture."""
    found = []

    def rec(n, top=False):
        if isinstance(n, _NESTED) and not top:
            return
        if isinstance(n, ast.JoinedStr):
            for part in n.values:
                if isinstance(part, ast.FormattedValue) and isinstance(part.value, ast.Name) \
                        and isinstance(part.value.ctx, ast.Load):
                    found.append((part.value.id, part.value.lineno))
        for sub in ast.iter_child_nodes(n):
            rec(sub)

    rec(node, top=True)
    return found


def _captures(path: pathlib.Path) -> list:
    """Every f-string in `path` that formats a module-level callable/module through a free name."""
    tree = _parse(path)
    mod = _module_bindings(tree)
    bad = []
    where = path.relative_to(PKG) if PKG in path.parents else path.name

    def walk(node, scope: frozenset):
        for name, lineno in _fstring_names(node):
            if name in scope or hasattr(builtins, name) or name not in mod:
                continue
            if _classify(path, name) in ("callable", "module"):
                bad.append(f"{where}:{lineno} in {getattr(node, 'name', '<module>')}(): f-string "
                           f"formats module-level {name!r} -- did you mean a parameter of that name?")
        for sub in ast.iter_child_nodes(node):
            _descend(sub, scope)

    def _descend(node, scope: frozenset):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            walk(node, scope | _binds(node))
        else:
            for sub in ast.iter_child_nodes(node):
                _descend(sub, scope)

    for top in tree.body:
        _descend(top, frozenset())
    return bad


def test_no_diagnostic_formats_a_module_level_function():
    """The whole package, every f-string. See the module docstring for the shipped defect."""
    problems = []
    for path in sorted(PKG.rglob("*.py")):
        problems += _captures(path)
    assert problems == [], "\n" + "\n".join(problems)


def test_the_guard_actually_catches_the_shipped_shape(tmp_path):
    """A check that cannot fail is worse than no check: rebuild the exact defect and prove the scan
    fails on it -- and that formatting a module-level CONSTANT stays legal."""
    src = tmp_path / "probe.py"
    src.write_text(
        "from ff9mapkit.eb.labelasm import label\n"
        "from ff9mapkit.flags import FIRST_SAFE_FLAG\n"
        "\n"
        "def refuse(x):\n"
        "    raise ValueError(f'{label} {x!r}: unknown unit')\n"
        "\n"
        "def fine(x):\n"
        "    raise ValueError(f'flag {x} < {FIRST_SAFE_FLAG}')\n"
        "\n"
        "def also_fine(x, label='hud value'):\n"
        "    raise ValueError(f'{label} {x!r}: unknown unit')\n"
        "\n"
        "def outer(label):\n"
        "    def inner(x):\n"
        "        raise ValueError(f'{label} {x!r}: closed over, not captured')\n"
        "    return inner\n",
        encoding="utf-8")
    found = _captures(src)
    assert len(found) == 1, found
    assert "'label'" in found[0] and "refuse()" in found[0]
