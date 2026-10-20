"""THE CELL-CLIPPED FILL in game: put the lab in the live install for ONE session, swap its variant, take it out.

  install VARIANT    refuse while FF9 runs or a lab is already there; back Memoria.ini up into the MAIN repo's
                     backups/ (worktree-parked backups get lost), copy out/VARIANT/FF9CustomMap-lab into the install
                     and put it FIRST in FolderNames (bytes edited in place, nothing else touched)
  swap VARIANT       refuse while FF9 runs; replace the installed lab's contents with out/VARIANT's (the ini is not
                     touched: the folder name stays the same)
  uninstall RUN_DIR  refuse while FF9 runs; take ONLY the lab's own FolderNames entry back out (bytes, in place) and
                     check the ini is then the backup byte for byte -- a mismatch means another session edited it
                     meanwhile, and that edit is kept, not clobbered; move the lab out of the install into RUN_DIR
                     (a lab left in the install is activated by the next launcher run)
State: out/install.json (which variant is installed).
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
MAIN_BACKUPS = Path(r"C:\gd\Dream-World-IX\backups")
LAB_NAME = "FF9CustomMap-lab"
OUT = HERE / "out"
STATE = OUT / "install.json"
INI = GAME / "Memoria.ini"
ENTRY = b'"' + LAB_NAME.encode() + b'", '


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def game_running() -> bool:
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq FF9.exe"], capture_output=True, text=True).stdout
    return "FF9.exe" in out


def tree_sha(root: Path) -> str:
    h = hashlib.sha256()
    for p in sorted(q for q in root.rglob("*") if q.is_file()):
        h.update(p.relative_to(root).as_posix().encode() + b"\0" + p.read_bytes())
    return h.hexdigest()


def install(variant: str):
    src = OUT / variant / LAB_NAME
    if not src.is_dir():
        raise SystemExit(f"no {src}: run lab_build.py first")
    if game_running():
        raise SystemExit("FF9 is running: close it first (the ini is read at launch)")
    if (GAME / LAB_NAME).exists():
        raise SystemExit(f"{GAME / LAB_NAME} already exists: another lab is in the install -- not touching it")
    raw = INI.read_bytes()
    m = re.search(rb'^(\s*FolderNames\s*=\s*)(.+)$', raw, re.M)
    if not m:
        raise SystemExit("no FolderNames line in Memoria.ini")
    if LAB_NAME.encode() in m.group(2):
        raise SystemExit(f"{LAB_NAME} is already in FolderNames: {m.group(2)!r}")
    stamp = time.strftime("%Y%m%d-%H%M%S")
    MAIN_BACKUPS.mkdir(parents=True, exist_ok=True)
    bak = MAIN_BACKUPS / f"Memoria.ini.{stamp}.cellclip-lab"
    shutil.copyfile(INI, bak)
    assert sha(bak) == sha(INI)
    shutil.copytree(src, GAME / LAB_NAME)
    INI.write_bytes(raw[:m.start(2)] + ENTRY + raw[m.start(2):])
    STATE.write_text(json.dumps({"backup": str(bak), "ini_sha": sha(bak), "installed_at": stamp,
                                 "variant": variant, "lab_sha": tree_sha(GAME / LAB_NAME)}, indent=1),
                     encoding="utf-8")
    print(f"installed {variant}: {GAME / LAB_NAME}; ini backed up to {bak} (sha {sha(bak)[:16]}); "
          f"FolderNames now starts with {LAB_NAME}")


def swap(variant: str):
    if game_running():
        raise SystemExit("FF9 is running: close it first (the overrides are read at world load)")
    st = json.loads(STATE.read_text(encoding="utf-8"))
    lab = GAME / LAB_NAME
    if tree_sha(lab) != st["lab_sha"]:
        raise SystemExit("the installed lab is not the one this script put there -- not touching it")
    shutil.rmtree(lab)
    shutil.copytree(OUT / variant / LAB_NAME, lab)
    st.update(variant=variant, lab_sha=tree_sha(lab))
    STATE.write_text(json.dumps(st, indent=1), encoding="utf-8")
    print(f"swapped: the installed lab is now {variant}")


def uninstall(run_dir: Path):
    if game_running():
        raise SystemExit("FF9 is running: close it first")
    st = json.loads(STATE.read_text(encoding="utf-8"))
    raw = INI.read_bytes()
    if raw.count(ENTRY) != 1:
        raise SystemExit(f"FolderNames carries the lab entry {raw.count(ENTRY)} times -- fix Memoria.ini by hand")
    INI.write_bytes(raw.replace(ENTRY, b"", 1))
    same = sha(INI) == st["ini_sha"]
    lab = GAME / LAB_NAME
    if lab.exists():
        run_dir.mkdir(parents=True, exist_ok=True)
        shutil.move(str(lab), str(run_dir / f"{LAB_NAME}.moved"))
    STATE.unlink()
    print(f"uninstalled: the lab entry is out of FolderNames; the ini is "
          + ("the backup byte for byte" if same else f"NOT the backup ({st['backup']}): another edit landed meanwhile "
             f"and was kept") + f"; the lab moved into {run_dir}")


if __name__ == "__main__":
    if sys.argv[1:2] == ["install"] and len(sys.argv) == 3:
        install(sys.argv[2])
    elif sys.argv[1:2] == ["swap"] and len(sys.argv) == 3:
        swap(sys.argv[2])
    elif sys.argv[1:2] == ["uninstall"] and len(sys.argv) == 3:
        uninstall(Path(sys.argv[2]))
    else:
        raise SystemExit(__doc__)
