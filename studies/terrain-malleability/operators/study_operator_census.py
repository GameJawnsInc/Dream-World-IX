"""Operator inventory, step 2: which STUDY scripts are *operators* (write terrain), and which of those
did the kit absorb (named by a world/ module or its tests) vs. never productize.

READ-ONLY. For every .py under studies/overworld-topography, studies/path-d-new-world (+ subdirs) and
studies/coast-shape-language, this records:
  * writes_signals  : static markers that the script WRITES terrain (deploy_override / write_ff9mesh /
                      deploy_donor_sidecar / auto_mirror / a --deploy flag / an explicit mod-folder write)
  * kit_refs        : kit modules (ff9mapkit/ff9mapkit/world/*.py, and tests/) whose text names the script
                      (by file stem) -- i.e. the productization trail
  * doc1            : first docstring line (the script's own claim of what it is)
Output: out/study_operator_census.json  (+ a short stdout summary).  The OPERATOR set = writes_signals != [].
A script that writes AND has no kit_refs is a candidate "study-only operator"; the hand curation of which of
those carry a *proven law* lives in NOTES.md (this script only does the mechanical part).

Rerun:  py studies/terrain-malleability/operators/study_operator_census.py
"""
import ast, json, os, re, sys

sys.path.insert(0, r"C:\gd\Dream-World-IX\ff9mapkit")
REPO = r"C:\gd\Dream-World-IX"
STUDY_DIRS = [
    "studies/overworld-topography",
    "studies/path-d-new-world",
    "studies/coast-shape-language",
]
KIT_DIRS = [r"ff9mapkit\ff9mapkit\world", r"ff9mapkit\tests", r"tools"]
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
os.makedirs(OUT, exist_ok=True)

WRITE_PATTERNS = {
    "deploy_override": r"\bdeploy_override\s*\(",
    "write_ff9mesh": r"\bwrite_ff9mesh\s*\(",
    "deploy_donor_sidecar": r"\bdeploy_donor_sidecar\s*\(",
    "auto_mirror": r"\bauto_mirror\s*\(",
    "kit_deploy_call": r"\b(?:T|terrain|island|interior|transplant|coastmorph)\.(?:reclaim|coast|reshape|deploy\w*|mint\w*|carry\w*)\s*\(",
    "--deploy": r"[\"']--deploy[\"']",
    "FF9CustomMap-write": r"FF9CustomMap[-\w]*[\"'].{0,60}(?:write|open\(.+[\"']w)",
}


def py_files():
    for d in STUDY_DIRS:
        base = os.path.join(REPO, d)
        for root, dirs, files in os.walk(base):
            dirs[:] = [x for x in dirs if x not in ("__pycache__", "out")]
            for f in files:
                if f.endswith(".py"):
                    yield os.path.join(root, f)


def doc1(src):
    try:
        t = ast.parse(src)
        d = ast.get_docstring(t) or ""
        return " ".join(d.strip().split())[:220]
    except SyntaxError:
        return "(syntax error)"


# preload kit text corpus (small: python files only)
corpus = {}
for kd in KIT_DIRS:
    base = os.path.join(REPO, kd)
    for root, dirs, files in os.walk(base):
        dirs[:] = [x for x in dirs if x not in ("__pycache__",)]
        for f in files:
            if f.endswith(".py"):
                p = os.path.join(root, f)
                try:
                    corpus[os.path.relpath(p, REPO)] = set(re.findall(r"[A-Za-z0-9_]+", open(p, encoding="utf-8", errors="replace").read()))
                except OSError:
                    pass

rows = []
for p in sorted(py_files()):
    src = open(p, encoding="utf-8", errors="replace").read()
    stem = os.path.splitext(os.path.basename(p))[0]
    sig = [k for k, pat in WRITE_PATTERNS.items() if re.search(pat, src)]
    refs = sorted(k for k, toks in corpus.items() if stem in toks)
    rows.append({
        "path": os.path.relpath(p, REPO).replace("\\", "/"),
        "stem": stem,
        "lines": src.count("\n") + 1,
        "writes_signals": sig,
        "kit_refs": refs,
        "doc1": doc1(src),
    })

json.dump(rows, open(os.path.join(OUT, "study_operator_census.json"), "w", encoding="utf-8"), indent=1)

ops = [r for r in rows if r["writes_signals"]]
absorbed = [r for r in ops if r["kit_refs"]]
study_only = [r for r in ops if not r["kit_refs"]]
print(f"scripts scanned: {len(rows)}; WRITE-capable (operators): {len(ops)}; named by kit/tests/tools: {len(absorbed)}; "
      f"write-capable with NO kit reference: {len(study_only)}")
print("--- write-capable, no kit reference ---")
for r in study_only:
    print(f"{r['path']:70s} {','.join(r['writes_signals'])}")
