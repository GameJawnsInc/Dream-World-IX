"""Bulk-extract every real field's .bgi to the scratch census dir (read-only on the install)."""
import json, re, sys, time
from pathlib import Path

sys.path.insert(0, r"C:/gd/Dream-World-IX/.claude/worktrees/unruffled-moser-861897/ff9mapkit")
import UnityPy

SA = Path(r"C:/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX/StreamingAssets")
OUT = Path(__file__).resolve().parent / "bgi"
OUT.mkdir(exist_ok=True)

idx = json.load(open(SA / ".ff9mapkit-field-index.json"))
by_bundle = {}
for folder, bundle in idx.items():
    by_bundle.setdefault(bundle, set()).add(folder)

done = 0
for bundle, folders in sorted(by_bundle.items()):
    t0 = time.time()
    env = UnityPy.load(str(SA / bundle))
    got = 0
    for k, obj in env.container.items():
        kl = k.lower()
        m = re.search(r"fieldmaps/([^/]+)/", kl)
        if not m or not kl.endswith(".bgi.bytes"):
            continue
        folder = m.group(1)
        if folder not in folders:
            continue
        p = OUT / f"{folder}.bgi"
        if p.exists():
            continue
        data = obj.read()
        raw = getattr(data, "script", None) or getattr(data, "m_Script", None) or getattr(data, "raw_data", None)
        if raw is None:
            continue
        if isinstance(raw, str):
            raw = raw.encode("utf-8", "surrogateescape")
        p.write_bytes(bytes(raw))
        got += 1
    done += got
    print(f"{bundle}: {got} bgi  ({time.time()-t0:.1f}s)", flush=True)
print("TOTAL", done)
