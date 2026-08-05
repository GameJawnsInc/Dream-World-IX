"""VERIFY the palette shortlist -- run every candidate through a real --dry-run.

palette_census.py enumerates rects offline over the cached mask; it cannot know whether
excise's assemblies are vertex-separable or whether the fill triangulates. Only the real
gate stack knows. This runs each shortlist row and records the verdict, so the palette we
quote is measured rather than predicted.

  py studies/coast-shape-language/palette_verify.py [--disc 1]

Writes out/palette_verified.json. Read-only: every run is --dry-run.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
KIT = HERE.parents[1] / "ff9mapkit"


def run(donor, size, disc):
    cmd = [sys.executable, "-m", "ff9mapkit", "world-transplant",
           "--mod-folder", "FF9CustomMap-world",
           "--cell", "18,3", "--donor", f"{donor[0]},{donor[1]}",
           "--size", f"{size[0]}x{size[1]}", "--shift", "0,0", "--excise",
           "--disc", str(disc), "--target-disc", "9", "--all-sea-target",
           "--skip-mirror", "--dry-run"]
    try:
        r = subprocess.run(cmd, cwd=KIT, capture_output=True, text=True, timeout=900)
    except subprocess.TimeoutExpired:
        return dict(ok=False, why="TIMEOUT")
    out = r.stdout + r.stderr
    if "dry run: gates CLEAN" in out:
        return dict(ok=True, why="gates CLEAN")
    m = re.search(r"--excise refused: (.+)", out)
    if m:
        return dict(ok=False, why="excise refused: " + m.group(1).strip()[:90])
    fails = re.findall(r"GATE ([a-z0-9\-\[\]]+):.*?-> FAIL", out)
    if fails:
        return dict(ok=False, why="gate FAIL: " + ", ".join(dict.fromkeys(fails))[:90])
    m = re.search(r"(ConfigError|ValueError|Error): (.+)", out)
    return dict(ok=False, why=(m.group(2)[:90] if m else "unknown"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--disc", type=int, default=1)
    args = ap.parse_args()
    rows = json.loads((HERE / "out" / f"palette_d{args.disc}.json").read_text())["masses"]
    print(f"verifying {len(rows)} shortlist rows (real --dry-run each)\n")
    results = []
    for i, r in enumerate(rows, 1):
        v = run(r["donor"], r["size"], args.disc)
        results.append(dict(r, **{"verified": v["ok"], "why": v["why"]}))
        mark = "OK  " if v["ok"] else "no  "
        print(f"  [{i:>2}/{len(rows)}] {mark} {str(tuple(r['donor'])):>9} "
              f"{r['size'][0]}x{r['size'][1]}  {r['area']:>6.0f}u2  {v['why']}",
              flush=True)
    ok = [r for r in results if r["verified"]]
    print(f"\nVERIFIED PALETTE: {len(ok)} of {len(results)} carry clean")
    for r in sorted(ok, key=lambda r: -r["area"]):
        how = "clean carry" if r["excise_cells"] == 0 \
            else f"excise {r['excise_cells']} cells"
        print(f"   {str(tuple(r['donor'])):>9} {r['size'][0]}x{r['size'][1]}  "
              f"{r['area']:>6.0f}u2  relief {r['relief']:>5.1f}  walk {r['walk']:.2f}  "
              f"{how}")
    (HERE / "out" / f"palette_verified_d{args.disc}.json").write_text(
        json.dumps(results, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
