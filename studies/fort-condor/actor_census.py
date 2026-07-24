"""Actor-budget census over the 817 HW field-script exports (rung 0, fort-condor study).

For every reference/test2 export, count:
  - entries        : script entries in the .eb (max `#HW newentry N` + 1, first copy only --
                     some exports repeat the whole script for a second language variant)
  - model_actors   : entries whose body contains SetModel( (model-bearing NPCs/monsters/props)
  - init_at_boot   : InitObject/InitCode calls inside Main_Init (simultaneous residents at field boot)
  - runtime_spawns : InitObject calls OUTSIDE Main_Init (dynamic mid-scene spawning)

Prints the distribution + the top crowd fields, joined to reference/field-manifest.tsv.

Usage:  py studies/fort-condor/actor_census.py [--top N]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

EXPORTS = Path(r"C:\gd\FFIX\reference\test2")
MANIFEST = Path(r"C:\gd\Dream-World-IX\reference\field-manifest.tsv")

RE_ENTRY = re.compile(r"^#HW newentry (\d+)")
RE_FUNC = re.compile(r"^Function (\S+)")
RE_INITOBJ = re.compile(r"\b(?:InitObject|InitCode)\(")


def load_manifest() -> dict[str, tuple[int, str]]:
    out: dict[str, tuple[int, str]] = {}
    for line in MANIFEST.read_text(encoding="utf-8").splitlines():
        parts = line.split("\t")
        if len(parts) >= 3:
            out[parts[0]] = (int(parts[1]), parts[2])
    return out


def census_file(path: Path) -> dict:
    entries_seen: set[int] = set()
    model_entries: set[int] = set()
    init_at_boot = 0
    runtime_spawns = 0
    cur_entry = -1
    in_main_init = False
    first_copy_done = False

    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = RE_ENTRY.match(line)
        if m:
            n = int(m.group(1))
            if n == 0 and 0 in entries_seen:
                first_copy_done = True  # the export repeats the script; stop at copy 2
            if first_copy_done:
                break
            entries_seen.add(n)
            cur_entry = n
            in_main_init = False
            continue
        fm = RE_FUNC.match(line)
        if fm:
            in_main_init = fm.group(1) == "Main_Init"
            continue
        if "SetModel(" in line and cur_entry >= 0:
            model_entries.add(cur_entry)
        if RE_INITOBJ.search(line):
            if in_main_init:
                init_at_boot += 1
            else:
                runtime_spawns += 1

    return {
        "entries": (max(entries_seen) + 1) if entries_seen else 0,
        "model_actors": len(model_entries),
        "init_at_boot": init_at_boot,
        "runtime_spawns": runtime_spawns,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=15)
    args = ap.parse_args()

    manifest = load_manifest()
    rows = []
    for path in sorted(EXPORTS.glob("test2_*.txt")):
        stats = census_file(path)
        fid, name = manifest.get(path.name, (-1, "?"))
        rows.append({"file": path.name, "fid": fid, "name": name, **stats})

    if not rows:
        print(f"no exports found under {EXPORTS}", file=sys.stderr)
        return 1

    for key, label in [
        ("entries", "script entries per field"),
        ("model_actors", "model-bearing actors per field"),
        ("init_at_boot", "objects initialized in Main_Init"),
    ]:
        vals = sorted(r[key] for r in rows)
        n = len(vals)
        print(f"\n== {label} ==")
        print(
            f"  n={n}  min={vals[0]}  p50={vals[n // 2]}  p90={vals[int(n * 0.9)]}"
            f"  p99={vals[int(n * 0.99)]}  max={vals[-1]}"
        )
        print(f"  top {args.top}:")
        for r in sorted(rows, key=lambda r: -r[key])[: args.top]:
            print(
                f"    {r[key]:4d}  field {r['fid']:4d}  {r['name']:<28}"
                f" (entries={r['entries']}, models={r['model_actors']},"
                f" boot={r['init_at_boot']}, runtime={r['runtime_spawns']})"
            )

    spawners = [r for r in rows if r["runtime_spawns"] > 0]
    print(f"\n== runtime (non-Main_Init) InitObject spawning ==")
    print(f"  fields with runtime spawns: {len(spawners)} / {len(rows)}")
    for r in sorted(spawners, key=lambda r: -r["runtime_spawns"])[: args.top]:
        print(f"    {r['runtime_spawns']:4d}  field {r['fid']:4d}  {r['name']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
