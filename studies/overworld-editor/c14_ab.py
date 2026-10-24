"""A/B on real bytes: world-transplant (7,17) onto (0,3) by the old code (main repo master) and the new (this
worktree), plain and with --redress-orphans, each on a fresh draft of FF9CustomMap-world; the orphan gate's report
and every world file compared."""
import hashlib, json, subprocess, sys
from pathlib import Path
WT = Path(r"C:\gd\Dream-World-IX\.claude\worktrees\terrain-shaping-continue-4647b2\ff9mapkit")
MAIN = Path(r"C:\gd\Dream-World-IX\ff9mapkit")
sys.path.insert(0, str(WT))
from ff9mapkit.world import draft as D
GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
OUT = Path(sys.argv[1]); CELL = sys.argv[2]

def world(root):
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (root / "FF9_Data" / "WorldMap").rglob("Block*") if ".bak-" not in p.name}
res = {}
for code, kit in (("old", MAIN), ("new", WT)):
    for mode, extra in (("plain", []), ("redress", ["--redress-orphans"])):
        key = f"{code}-{mode}"
        d = D.ensure_draft(GAME / "FF9CustomMap-world", game=GAME, root=OUT / key)
        rep = OUT / f"{key}.json"
        r = subprocess.run([sys.executable, "-m", "ff9mapkit", "--game", str(GAME), "world-transplant", "--mod-folder",
                            str(d), "--cell", CELL, "--donor", "7,17", "--report-json", str(rep)] + extra,
                           cwd=kit, capture_output=True, text=True, timeout=1800)
        v = json.loads(rep.read_text()) if rep.is_file() else {}
        og = next((g for g in v.get("gates") or [] if g.get("gate") == "orphan-decals"), {})
        res[key] = {"rc": r.returncode, "ok": v.get("ok"), "world": world(d),
                    "orphan": {k: og.get(k) for k in ("ring_blocks", "n_orphans", "n_redressed", "cells", "detail")}}
        print(key, "rc", r.returncode, "ok", v.get("ok"), res[key]["orphan"])
        if r.returncode:
            print(r.stdout[-800:], r.stderr[-800:])
for mode in ("plain", "redress"):
    a, b = res[f"old-{mode}"]["world"], res[f"new-{mode}"]["world"]
    diff = sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))
    print(f"{mode}: old vs new {'IDENTICAL' if not diff else 'DIFFER: ' + str(diff)} over {len(a)} world files")
(OUT / "ab.json").write_text(json.dumps({k: {**v, "world": len(v["world"])} for k, v in res.items()}, indent=1))
