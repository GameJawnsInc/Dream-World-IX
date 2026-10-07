"""Operator inventory helper: dump the public defs/classes of chosen world/ modules with the first N lines
of each docstring (and the arg names), so the operator-by-operator facts in NOTES.md are traceable to a
mechanical read of the kit's own docstrings rather than memory.

READ-ONLY (AST parse, no import).  Rerun:
    py studies/terrain-malleability/operators/defs_digest.py transplant coastmorph island interior --lines 10
Writes out/defs_digest_<module>.txt for each module named.
"""
import argparse, ast, os, sys

ROOT = r"C:\gd\Dream-World-IX\ff9mapkit\ff9mapkit\world"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
os.makedirs(OUT, exist_ok=True)

ap = argparse.ArgumentParser()
ap.add_argument("modules", nargs="+")
ap.add_argument("--lines", type=int, default=8)
ap.add_argument("--private", action="store_true", help="include _private defs")
a = ap.parse_args()

for m in a.modules:
    p = os.path.join(ROOT, m + ".py")
    src = open(p, encoding="utf-8").read()
    t = ast.parse(src)
    out = [f"# {m}.py  ({src.count(chr(10)) + 1} lines)\n"]
    for n in t.body:
        if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and (a.private or not n.name.startswith("_")):
            kind = "class" if isinstance(n, ast.ClassDef) else "def"
            args = ""
            if isinstance(n, ast.FunctionDef):
                args = ", ".join(x.arg for x in n.args.args + n.args.kwonlyargs)
            doc = (ast.get_docstring(n) or "").strip().splitlines()[: a.lines]
            out.append(f"{kind} {n.name}({args})   L{n.lineno}-{getattr(n, 'end_lineno', n.lineno)}")
            for ln in doc:
                out.append("    " + ln.rstrip())
            out.append("")
    dest = os.path.join(OUT, f"defs_digest_{m}.txt")
    open(dest, "w", encoding="utf-8").write("\n".join(out))
    print("wrote", dest, len(out), "lines")
