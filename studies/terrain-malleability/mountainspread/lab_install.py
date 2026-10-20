"""Put the lab in the live install for ONE session, then take it out again (rounds 15-19's procedure, scripted).

  install            refuse while FF9 runs or a lab is already there; back Memoria.ini up into the MAIN repo's
                     backups/ (worktree-parked backups get lost), copy out/lab/island/FF9CustomMap-lab into the
                     install, and put it FIRST in FolderNames (bytes edited in place, nothing else touched)
  uninstall RUN_DIR  refuse while FF9 runs; restore Memoria.ini from that backup and check its sha against the one
                     recorded at install; move the lab out of the install into RUN_DIR (a lab left in the install is
                     activated by the next launcher run: round 14)
State: out/lab/install.json.
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
SRC = HERE / "out" / "lab" / "island" / LAB_NAME
STATE = HERE / "out" / "lab" / "install.json"
INI = GAME / "Memoria.ini"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def game_running() -> bool:
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq FF9.exe"], capture_output=True, text=True).stdout
    return "FF9.exe" in out


def install():
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
    bak = MAIN_BACKUPS / f"Memoria.ini.{stamp}.mountain-spread"
    shutil.copyfile(INI, bak)
    assert sha(bak) == sha(INI)
    shutil.copytree(SRC, GAME / LAB_NAME)
    new = raw[:m.start(2)] + b'"' + LAB_NAME.encode() + b'", ' + raw[m.start(2):]
    INI.write_bytes(new)
    STATE.write_text(json.dumps({"backup": str(bak), "ini_sha": sha(bak), "installed_at": stamp,
                                 "folder_names_before": m.group(2).decode(errors="replace")}, indent=1),
                     encoding="utf-8")
    print(f"installed: {GAME / LAB_NAME}; ini backed up to {bak} (sha {sha(bak)[:16]}); FolderNames now starts "
          f"with {LAB_NAME}")


def uninstall(run_dir: Path):
    if game_running():
        raise SystemExit("FF9 is running: close it first")
    st = json.loads(STATE.read_text(encoding="utf-8"))
    bak = Path(st["backup"])
    shutil.copyfile(bak, INI)
    if sha(INI) != st["ini_sha"]:
        raise SystemExit(f"Memoria.ini restore MISMATCH: {sha(INI)} vs {st['ini_sha']}")
    lab = GAME / LAB_NAME
    if lab.exists():
        run_dir.mkdir(parents=True, exist_ok=True)
        shutil.move(str(lab), str(run_dir / f"{LAB_NAME}.moved"))
    STATE.unlink()
    print(f"uninstalled: Memoria.ini restored byte-exact (sha {st['ini_sha'][:16]}); the lab moved into {run_dir}")


if __name__ == "__main__":
    if sys.argv[1:2] == ["install"]:
        install()
    elif sys.argv[1:2] == ["uninstall"] and len(sys.argv) == 3:
        uninstall(Path(sys.argv[2]))
    else:
        raise SystemExit(__doc__)
