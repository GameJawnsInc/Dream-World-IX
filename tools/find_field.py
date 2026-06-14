"""Map a FF9 field id (or name substring) -> its all-fields-import folder.

Usage:
    py tools/find_field.py 1860          # by field id
    py tools/find_field.py inn           # by FBG / EVT-name substring
    py tools/find_field.py "Cargo Room"  # by friendly manifest name

Prints  <field_id>  <friendly name>  <folder path>  for every match.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IMPORT_DIR = ROOT / "reference" / "all-fields-import"

sys.path.insert(0, str(ROOT / "ff9mapkit"))
from ff9mapkit._fieldtable import FBG_TO_EVT  # noqa: E402

# field id -> friendly name, from the HW manifest (col2 = id, col3 = name)
NAMES = {}
manifest = ROOT / "reference" / "field-manifest.tsv"
if manifest.exists():
    for line in manifest.read_text(encoding="utf-8", errors="replace").splitlines():
        parts = line.split("\t")
        if len(parts) >= 3 and parts[1].isdigit():
            NAMES.setdefault(int(parts[1]), parts[2])

# folder leaf name (UPPER FBG) -> full path under all-fields-import
FOLDERS = {p.name: p for p in IMPORT_DIR.glob("*/*") if p.is_dir()}


def folder_for(fbg):
    return FOLDERS.get(fbg.upper())


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    q = " ".join(sys.argv[1:])
    rows = []
    for fbg, (fid, evt) in FBG_TO_EVT.items():
        name = NAMES.get(fid, "")
        hay = f"{fid} {fbg} {evt} {name}".lower()
        if q.isdigit():
            hit = str(fid) == q
        else:
            hit = q.lower() in hay
        if hit:
            path = folder_for(fbg)
            rows.append((fid, name, evt, path))
    rows.sort()
    if not rows:
        print(f"no field matches {q!r}")
        return
    for fid, name, evt, path in rows:
        loc = path if path else "(not in all-fields-import)"
        print(f"{fid:>5}  {name or evt:<28}  {loc}")


if __name__ == "__main__":
    main()
