"""Study builder for a multi-instance ROOT (probe P1) -- RECON.md design A.

SUPERSEDED by tools/harness/instance.py (`py tools/harness/instance.py ensure|verify|teardown <root>`), which adopted the
roots this built. Kept as the probe record: its `verify` knows only the old 3-key overlay, so it reports every refreshed
root (whose [Netsync] is now parked off the owner's port and code) as drifted.

!! TEAR A ROOT DOWN ONLY WITH `teardown` BELOW, never any other way: a recursive delete that follows the junctions (PowerShell
!! 5.1's Remove-Item -Recurse is known to) deletes the REAL install's StreamingAssets and mod folders.

    py instance_root.py build    <root>     # create (refuses if <root> exists)
    py instance_root.py verify   <root>     # every junction resolves to its target, every copy hash-matches
    py instance_root.py teardown <root>     # THE TEARDOWN LAW: os.rmdir each junction, prove none left, then real files
    py instance_root.py fingerprint         # print the install fingerprint (what teardown must leave untouched)

The root is a REAL directory outside the Steam folder. Junctions (no admin needed) for the big read-only trees; COPIES (never
hardlinks, so no file shares an inode with the install) of everything an instance writes or that sits beside its exe.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

INSTALL = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
EXE_FILES = ["FF9.exe", "steam_api64.dll", "XAudio2_9.dll", "msvcp120.dll", "msvcr100.dll", "msvcr120.dll"]
DATA_DIRS = ["Managed", "Mono", "Plugins", "Resources"]          # x64\FF9_Data junctions
INI_OVERLAY = [("Netsync", "Enabled", "0"), ("Control", "AlwaysCaptureGamepad", "0"), ("SfxProbe", "Enabled", "0")]


def folder_names(ini: bytes) -> list:
    m = re.search(rb'(?m)^FolderNames\s*=\s*(.*)$', ini)
    return [x.decode() for x in re.findall(rb'"([^"]+)"', m.group(1))] if m else []


def plan(root: Path) -> dict:
    ini = (INSTALL / "Memoria.ini").read_bytes()
    root_junctions = ["StreamingAssets", "FF9_Data"] + [f for f in folder_names(ini) if (INSTALL / f).is_dir()]
    links = {root / n: INSTALL / n for n in root_junctions}
    links.update({root / "x64" / "FF9_Data" / d: INSTALL / "x64" / "FF9_Data" / d for d in DATA_DIRS})
    copies = {root / "Settings.ini": INSTALL / "Settings.ini"}
    copies.update({root / "x64" / f: INSTALL / "x64" / f for f in EXE_FILES})
    for p in (INSTALL / "x64" / "FF9_Data").iterdir():
        if p.is_file() and p.name != "output_log.txt":
            copies[root / "x64" / "FF9_Data" / p.name] = p
    return {"links": links, "copies": copies, "ini_src": INSTALL / "Memoria.ini", "ini_dst": root / "Memoria.ini"}


def overlay(ini: bytes) -> bytes:
    for sec, key, val in INI_OVERLAY:
        i = ini.index(b"[" + sec.encode() + b"]")
        j = ini.find(b"\n[", i + 1)
        j = len(ini) if j < 0 else j
        body, n = re.subn(rb"(?m)^(" + key.encode() + rb"\s*=\s*)[^\r\n]*", lambda m: m.group(1) + val.encode(), ini[i:j])
        assert n == 1, (sec, key, n)
        ini = ini[:i] + body + ini[j:]
    return ini


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build(root: Path) -> None:
    assert not root.exists(), f"{root} exists -- teardown first"
    assert INSTALL not in root.parents and root.drive == INSTALL.drive, root
    pl = plan(root)
    (root / "x64" / "FF9_Data").mkdir(parents=True)
    pl["ini_dst"].write_bytes(overlay(pl["ini_src"].read_bytes()))
    for dst, src in pl["copies"].items():
        shutil.copy2(src, dst)
    for link, target in pl["links"].items():
        r = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)], capture_output=True, text=True)
        assert r.returncode == 0 and os.path.isjunction(link), (link, r.stdout, r.stderr)
    print(f"built {root}: {len(pl['links'])} junctions, {len(pl['copies'])} copies + Memoria.ini (overlay {INI_OVERLAY})")


def verify(root: Path) -> bool:
    pl, bad = plan(root), []
    for link, target in pl["links"].items():
        if not os.path.isjunction(link) or Path(os.path.realpath(link)) != Path(os.path.realpath(target)):
            bad.append(f"junction {link} -> {os.path.realpath(link) if link.exists() else 'MISSING'} (want {target})")
    for dst, src in pl["copies"].items():
        if not dst.is_file() or dst.stat().st_size != src.stat().st_size or sha(dst) != sha(src):
            bad.append(f"copy {dst}")
    want = overlay(pl["ini_src"].read_bytes())
    if pl["ini_dst"].read_bytes() != want:
        bad.append("Memoria.ini drifted from install+overlay")
    print(("VERIFY OK" if not bad else "VERIFY FAIL") + f": {len(pl['links'])} junctions, {len(pl['copies'])} copies"
          + "".join("\n  " + b for b in bad))
    return not bad


def teardown(root: Path) -> None:
    """THE TEARDOWN LAW: never a recursive delete that could follow a junction into the install."""
    assert root.is_dir() and not os.path.isjunction(root), root
    pl = plan(root)
    for link in pl["links"]:
        if os.path.lexists(link):
            assert os.path.isjunction(link), f"{link} is not a junction -- refusing"
            os.rmdir(link)                                   # removes the LINK only
    left = []
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        for d in dirnames:
            p = Path(dirpath) / d
            if os.path.isjunction(p) or os.path.islink(p):
                left.append(str(p))
    assert not left, f"reparse points left -- refusing to delete files: {left}"
    for dirpath, dirnames, filenames in os.walk(root, topdown=False, followlinks=False):
        for f in filenames:
            os.remove(Path(dirpath) / f)
        for d in dirnames:
            os.rmdir(Path(dirpath) / d)
    os.rmdir(root)
    print(f"torn down {root}")


def fingerprint() -> dict:
    ini = (INSTALL / "Memoria.ini").read_bytes()
    out = {}
    targets = ["StreamingAssets", "FF9_Data"] + folder_names(ini) + [f"x64/FF9_Data/{d}" for d in DATA_DIRS]
    for t in targets:
        p = INSTALL / t
        if not p.is_dir():
            continue
        n = size = 0
        newest = 0.0
        for dirpath, _, files in os.walk(p):
            for f in files:
                st = os.stat(Path(dirpath) / f)
                n += 1
                size += st.st_size
                newest = max(newest, st.st_mtime)
        out[t] = [n, size, round(newest, 3)]
    out["Memoria.ini"] = sha(INSTALL / "Memoria.ini")[:16]
    return out


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "fingerprint":
        print(json.dumps(fingerprint(), indent=1))
    else:
        root = Path(sys.argv[2])
        {"build": build, "verify": verify, "teardown": teardown}[cmd](root)
