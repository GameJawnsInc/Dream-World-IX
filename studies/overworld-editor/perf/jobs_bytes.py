"""Lane jobs: WRITTEN-BYTES identity of the kernel prototypes. For a verb, two fresh drafts of the live folder
(out/perf/jobs/bytes/, deleted after); the card's Accept calls run in a child process into each -- one unpatched, one
with the named prototype patches installed (jobs_census_proto P1/P2, jobs_delaunay_proto D1) -- and every file under
the two drafts is compared byte for byte (the ledger rows normalised for their utc and the draft's own path; a
backup's timestamp suffix normalised), plus the Accept's verdict JSON.

    py studies/overworld-editor/perf/jobs_bytes.py <verb> P1 [P2] [D1]     -> out/perf/jobs/bytes.json
    (child) py jobs_bytes.py child <verb> <draft> <out> [patches]
"""
import contextlib
import io
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import jobs_common as J  # noqa: E402


def tree(root):
    out = {}
    root = Path(root)
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(root).as_posix()
        if rel == "draft.json":
            continue
        if rel.endswith(".ff9world.jsonl"):
            rows = []
            for ln in p.read_text(encoding="utf-8").splitlines():
                if ln.strip():
                    e = json.loads(ln)
                    e.pop("utc", None)
                    row = json.dumps(e, sort_keys=True).replace(json.dumps(str(root))[1:-1], "<D>")
                    rows.append(re.sub(r"jobs_by_[A-Za-z0-9_]+", "<T>", row))
            out[rel] = "\n".join(rows).encode()
        elif ".bak-" in p.name:
            out[re.sub(r"\.bak-\d{8}-\d{6}.*$", ".bak-TS", rel)] = p.read_bytes()
        else:
            out[rel] = p.read_bytes()
    return out


def child(verb, draft, out, patches):
    if "P1" in patches or "P2" in patches:
        import jobs_census_proto as CP
        if "P1" in patches:
            CP.install_p1()
        if "P2" in patches:
            CP.install_p2()
    if "D1" in patches:
        import jobs_delaunay_proto as DP
        from ff9mapkit.world import island as IS
        IS._delaunay = DP.fast_delaunay
    from ff9mapkit import cli
    base = J.draft()
    tmp = Path(tempfile.mkdtemp(prefix="jobs_by_"))
    verdicts = []
    for a in J.accept_argvs(verb, base, tmp / "verdict.json", tmp / "verdict4.json"):
        a = [str(x).replace(str(base), str(draft)) for x in a]
        with contextlib.redirect_stdout(io.StringIO()):
            try:
                cli.main(a[3:])
            except SystemExit:
                pass
    for name in ("verdict.json", "verdict4.json"):
        if (tmp / name).is_file():
            v = json.loads((tmp / name).read_text(encoding="utf-8"))
            v["written"] = [str(w).replace(str(draft), "<D>") for w in v.get("written") or []]
            verdicts.append(v)
    Path(out).write_text(json.dumps(verdicts, sort_keys=True), encoding="utf-8")


def main():
    from ff9mapkit.world import draft as D
    verb = sys.argv[1]
    patches = sys.argv[2:]
    trees, verdicts = {}, {}
    for arm in ("unpatched", "patched"):
        root = J.OUT / "bytes" / arm
        if root.exists():
            shutil.rmtree(root)
        d = D.ensure_draft(J.SOURCE, game=J.GAME, root=root)
        out = Path(tempfile.mkdtemp(prefix="jobs_byx_")) / "v.json"
        subprocess.run([sys.executable, __file__, "child", verb, str(d), str(out)]
                       + (patches if arm == "patched" else []), cwd=str(J.kit_cwd()), check=True)
        verdicts[arm] = out.read_text(encoding="utf-8")
        trees[arm] = tree(d)
    tu, tp = trees["unpatched"], trees["patched"]
    diff = sorted(k for k in set(tu) | set(tp) if tu.get(k) != tp.get(k))
    edited = len(D.edits(J.OUT / "bytes" / "patched" / (J.SOURCE.name + ".draft")))
    vu = json.loads(verdicts["unpatched"])
    rec = {"verb": verb, "patches": patches, "files_compared": len(tu), "files_differ": diff[:10],
           "identical": not diff, "verdicts_identical": verdicts["unpatched"] == verdicts["patched"],
           "accept_ok": [v.get("ok") for v in vu], "draft_files_edited": edited}
    print(json.dumps(rec))
    p = J.OUT / "bytes.json"
    allr = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    allr[f"{verb}:{'+'.join(patches)}"] = rec
    p.write_text(json.dumps(allr, indent=1), encoding="utf-8")
    for arm in trees:
        shutil.rmtree(J.OUT / "bytes" / arm, ignore_errors=True)


if __name__ == "__main__":
    if sys.argv[1] == "child":
        child(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5:])
    else:
        main()
