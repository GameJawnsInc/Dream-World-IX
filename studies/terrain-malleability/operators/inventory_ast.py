"""Operator inventory, step 1: static AST census of the world/ package and the CLI verb table.

READ-ONLY. Parses (never imports, never runs) ff9mapkit/ff9mapkit/world/*.py and cli.py and writes
out/inventory_ast.json:
  * per world module: line count, module docstring (first 600 chars), public top-level defs with
    line numbers and the first docstring line
  * per `world-*` CLI verb: its handler, the `world.<module>.<fn>` symbols the handler touches
    (so the verb -> module/function edge is mechanical, not from memory), and its argparse flags

Rerun:  py studies/terrain-malleability/operators/inventory_ast.py
"""
import ast, json, os, re, sys

sys.path.insert(0, r"C:\gd\Dream-World-IX\ff9mapkit")
ROOT = r"C:\gd\Dream-World-IX\ff9mapkit\ff9mapkit"
WORLD = os.path.join(ROOT, "world")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
os.makedirs(OUT, exist_ok=True)


def first_line(doc):
    if not doc:
        return ""
    return doc.strip().splitlines()[0][:160]


def census_module(path):
    src = open(path, encoding="utf-8").read()
    tree = ast.parse(src)
    doc = ast.get_docstring(tree) or ""
    defs = []
    for n in tree.body:
        if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and not n.name.startswith("_"):
            defs.append({
                "name": n.name,
                "kind": "class" if isinstance(n, ast.ClassDef) else "def",
                "line": n.lineno,
                "end": getattr(n, "end_lineno", n.lineno),
                "doc1": first_line(ast.get_docstring(n)),
            })
    return {"lines": src.count("\n") + 1, "doc": doc[:600], "defs": defs}


mods = {}
for fn in sorted(os.listdir(WORLD)):
    if fn.endswith(".py"):
        mods[fn[:-3]] = census_module(os.path.join(WORLD, fn))

# ---- CLI verbs ----------------------------------------------------------------------------------
cli_path = os.path.join(ROOT, "cli.py")
cli_src = open(cli_path, encoding="utf-8").read()
cli_tree = ast.parse(cli_src)

handlers = {}  # func name -> {line, end, world symbols}
for n in cli_tree.body:
    if isinstance(n, ast.FunctionDef) and n.name.startswith("_cmd_world_"):
        syms = set()
        for sub in ast.walk(n):
            # patterns:  from .world import X as Y ; from .world.mod import fn ; mod.fn(...)
            if isinstance(sub, ast.ImportFrom) and sub.module and "world" in (sub.module or ""):
                for a in sub.names:
                    syms.add(f"{sub.module}.{a.name}")
            if isinstance(sub, ast.Import):
                for a in sub.names:
                    if "world" in a.name:
                        syms.add(a.name)
        handlers[n.name] = {"line": n.lineno, "end": n.end_lineno, "imports": sorted(syms)}

# parser table: scan main()/build_parser for  X = sub.add_parser("world-...") ; X.add_argument("--flag") ; X.set_defaults(func=H)
verbs = {}
var2verb = {}
for node in ast.walk(cli_tree):
    if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
        c = node.value
        if isinstance(c.func, ast.Attribute) and c.func.attr == "add_parser" and c.args:
            a0 = c.args[0]
            if isinstance(a0, ast.Constant) and isinstance(a0.value, str) and a0.value.startswith("world-"):
                var = node.targets[0].id if isinstance(node.targets[0], ast.Name) else None
                verbs.setdefault(a0.value, {"flags": [], "handler": None, "line": node.lineno})
                if var:
                    var2verb.setdefault(var, []).append((node.lineno, a0.value))


def verb_for(var, lineno):
    # a parser variable name is reused (wtp, wmt) -> pick the nearest preceding definition
    cands = [x for x in var2verb.get(var, []) if x[0] <= lineno]
    return max(cands)[1] if cands else None


for node in ast.walk(cli_tree):
    if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
        c = node.value
        f = c.func
        if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name):
            v = verb_for(f.value.id, node.lineno)
            if not v:
                continue
            if f.attr == "add_argument":
                flag = [a.value for a in c.args if isinstance(a, ast.Constant) and isinstance(a.value, str) and a.value.startswith("-")]
                verbs[v]["flags"].extend(flag)
            elif f.attr == "set_defaults":
                for kw in c.keywords:
                    if kw.arg == "func" and isinstance(kw.value, ast.Name):
                        verbs[v]["handler"] = kw.value.id

for v, d in verbs.items():
    h = handlers.get(d["handler"])
    d["handler_span"] = [h["line"], h["end"]] if h else None
    d["handler_imports"] = h["imports"] if h else []

json.dump({"modules": mods, "verbs": verbs}, open(os.path.join(OUT, "inventory_ast.json"), "w", encoding="utf-8"), indent=1)

print(f"{len(mods)} world modules, {sum(m['lines'] for m in mods.values())} lines; {len(verbs)} world-* verbs")
for v in sorted(verbs):
    d = verbs[v]
    print(f"{v:28s} {d['handler'] or '-':34s} L{d['handler_span'][0] if d['handler_span'] else '?'}-{d['handler_span'][1] if d['handler_span'] else '?'}  flags={len(d['flags'])}")
    for s in d["handler_imports"]:
        print(f"      imports {s}")
