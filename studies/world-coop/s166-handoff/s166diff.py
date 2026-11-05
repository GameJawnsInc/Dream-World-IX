"""Show the s166 delta: the clone vs the s165 snapshot taken before any s166 edit.
usage: py s166diff.py [--stat] [paths...]   (paths relative to Assembly-CSharp; default = every changed file)"""
import sys, os, difflib, pathlib
SNAP = pathlib.Path(__file__).parent / "s165base"
LIVE = pathlib.Path(r"C:\gd\FFIX\Memoria\Assembly-CSharp")
ROOTS = ["Global", "Memoria", "FF9", "UnityXInput", "Assets", "Assembly-CSharp.csproj"]
args = [a for a in sys.argv[1:] if not a.startswith("--")]
stat = "--stat" in sys.argv
def files(root):
    out = set()
    for r in ROOTS:
        p = root / r
        if p.is_file(): out.add(r)
        elif p.is_dir():
            for f in p.rglob("*"):
                if f.is_file() and f.suffix in (".cs", ".csproj"): out.add(str(f.relative_to(root)).replace("\\", "/"))
    return out
cands = sorted(files(SNAP) | files(LIVE)) if not args else args
for rel in cands:
    a = SNAP / rel; b = LIVE / rel
    ab = a.read_bytes() if a.exists() else b""
    bb = b.read_bytes() if b.exists() else b""
    if ab == bb: continue
    al = ab.decode("utf-8", "replace").splitlines(True); bl = bb.decode("utf-8", "replace").splitlines(True)
    d = list(difflib.unified_diff(al, bl, "s165/" + rel, "live/" + rel, n=3))
    if stat:
        add = sum(1 for l in d if l.startswith("+") and not l.startswith("+++")); rm = sum(1 for l in d if l.startswith("-") and not l.startswith("---"))
        crlf_a = ab.count(b"\r\n"); crlf_b = bb.count(b"\r\n")
        print(f"{rel}: +{add} -{rm}  (CRLF lines {crlf_a}->{crlf_b}, LF-only {ab.count(b'\n')-crlf_a}->{bb.count(b'\n')-crlf_b}){'  NEW' if not a.exists() else ''}")
    else:
        sys.stdout.writelines(d)
