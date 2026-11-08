#!/usr/bin/env python3
"""Build the s168 laptop update package (the README is TWO-PC-CHECKS-S168.md, the check is check-s168.ps1).

The s167 package (Desktop\\FF9Coop-laptop-update-20261106-s167) was assembled by hand; this is that recipe as a tool, with the
checks the s168 check script expects built in:

  dlls/x64|x86/          the six live DLLs (Assembly-CSharp.dll must be the s168 build: --s168-sha256)
  dlls-s167/x64|x86/     the s167 Assembly-CSharp.dll from the build's pre-s168 backup set (must be 12be3220520813a6...)
  FF9CustomMap-world/, FF9CustomMap-schema/, FF9CustomMap-msgs/   the three mod folders (tool backups `*.bak-*` and `*.lock` left out)
  FOLDERS-MANIFEST.txt   "<sha256> *<folder>/<path>" for every packaged mod-folder file
  DATA-WORLD-HASHES.txt  "<sha256 raw> <sha256 with every CR removed> *StreamingAssets/Data/World/<file>" (the fingerprint is CR-blind)
  HASHES.txt             "<sha256> *dlls/<arch>/<name>" (6) and "<sha256> *dlls-s167/<arch>/Assembly-CSharp.dll" (2)
  check-s168.ps1         copied as is (ASCII, CRLF)
  README.md              the sheet with every <PLACEHOLDER> filled and the packaging comment removed, CRLF; refused if one remains

It READS the install and backups/ and WRITES only the new package folder (refused if it exists) and its .zip. Run it with FF9 closed.

  py studies/field-coop/s168/build_package_s168.py --date 2026-11-08 --s168-sha256 <sha> --s167-backup-ts 20261107-233955 \\
      --bench-summary "<one line>" [--out-dir C:\\Users\\<you>\\Desktop] [--game <FF9 folder>]
"""
import argparse
import hashlib
import os
import re
import shutil
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SHEET = REPO / "studies" / "field-coop" / "TWO-PC-CHECKS-S168.md"
CHECK = REPO / "studies" / "field-coop" / "s168" / "check-s168.ps1"
BACKUPS = Path(r"C:\gd\Dream-World-IX\backups")
GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
S167_SHA256 = "12be3220520813a6dd4bc365b38a1f257eefe7819552b4f290bcefc9b0464096"
DLLS = ("Assembly-CSharp.dll", "Memoria.Prime.dll", "UnityEngine.UI.dll")
ARCHES = ("x64", "x86")
FOLDERS = ("FF9CustomMap-world", "FF9CustomMap-schema", "FF9CustomMap-msgs")
WORLD_DATA = ("Environment.txt", "TransportControls.csv", "WeatherColors.csv")
PLACEHOLDER = re.compile(r"<[A-Z][A-Z0-9_]*>")
PACKAGING_COMMENT = re.compile(r"<!-- Packaging.*?-->\s*", re.S)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fsha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def skipped(name: str) -> bool:
    return ".bak-" in name or name.endswith(".lock")


def fill_readme(text: str, values: dict) -> str:
    text = PACKAGING_COMMENT.sub("", text, count=1)
    for k, v in values.items():
        text = text.replace(f"<{k}>", v)
    left = sorted(set(PLACEHOLDER.findall(text)) - {"<FF9 folder>"})
    # angle-bracket words the sheet uses as prose (e.g. "<your FINAL FANTASY IX folder>") are lower-case; only UPPER tokens are placeholders
    if left:
        raise SystemExit(f"README: placeholder(s) left unfilled: {', '.join(left)}")
    return text.replace("\r\n", "\n").replace("\n", "\r\n")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--date", required=True, help="YYYY-MM-DD (the README title and the folder name)")
    ap.add_argument("--s168-sha256", required=True, help="the deployed s168 Assembly-CSharp.dll sha256 (both arches)")
    ap.add_argument("--s167-backup-ts", required=True, help="the build's pre-s168 backup set timestamp (backups/*.pre-s168.<ts>)")
    ap.add_argument("--bench-summary", required=True, help="one line: tonight's one-PC bench results")
    ap.add_argument("--out-dir", default=str(Path.home() / "Desktop"))
    ap.add_argument("--game", default=str(GAME))
    a = ap.parse_args(argv)

    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", a.date):
        raise SystemExit("--date must be YYYY-MM-DD")
    if not re.fullmatch(r"[0-9a-f]{64}", a.s168_sha256):
        raise SystemExit("--s168-sha256 must be 64 lower-case hex digits")
    game = Path(a.game)
    stamp = a.date.replace("-", "")
    name = f"FF9Coop-laptop-update-{stamp}-s168"
    out = Path(a.out_dir) / name
    if out.exists() or out.with_suffix(".zip").exists():
        raise SystemExit(f"refused: {out} (or its .zip) already exists")

    # the DLLs: live s168 (both arches) and the s167 backup set
    live = {(arch, d): game / arch / "FF9_Data" / "Managed" / d for arch in ARCHES for d in DLLS}
    for (arch, d), p in live.items():
        if not p.is_file():
            raise SystemExit(f"missing {p}")
    for arch in ARCHES:
        got = fsha(live[(arch, "Assembly-CSharp.dll")])
        if got != a.s168_sha256:
            raise SystemExit(f"the live {arch} Assembly-CSharp.dll is {got[:16]}, not the s168 build {a.s168_sha256[:16]}")
    old = {arch: BACKUPS / f"Assembly-CSharp.{arch}.dll.pre-s168.{a.s167_backup_ts}" for arch in ARCHES}
    for arch, p in old.items():
        if not p.is_file():
            raise SystemExit(f"missing the s167 backup {p}")
        if fsha(p) != S167_SHA256:
            raise SystemExit(f"{p} is not the s167 build ({fsha(p)[:16]})")

    out.mkdir(parents=True)
    hashes = []
    for arch in ARCHES:
        for d in DLLS:
            dst = out / "dlls" / arch / d
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(live[(arch, d)], dst)
            hashes.append(f"{fsha(dst)} *dlls/{arch}/{d}")
    for arch in ARCHES:
        dst = out / "dlls-s167" / arch / "Assembly-CSharp.dll"
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(old[arch], dst)
        hashes.append(f"{fsha(dst)} *dlls-s167/{arch}/Assembly-CSharp.dll")
    (out / "HASHES.txt").write_bytes(("\n".join(hashes) + "\n").encode("ascii"))

    # the three mod folders and their manifest
    manifest, counts = [], {}
    for f in FOLDERS:
        src = game / f
        if not src.is_dir():
            raise SystemExit(f"missing the mod folder {src}")
        n = 0
        for root, dirs, files in os.walk(src):
            dirs.sort()
            for fn in sorted(files):
                if skipped(fn):
                    continue
                s = Path(root) / fn
                rel = s.relative_to(game).as_posix()
                dst = out / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(s, dst)
                h = fsha(dst)
                if h != fsha(s):
                    raise SystemExit(f"copy drift on {rel}")
                manifest.append(f"{h} *{rel}")
                n += 1
        counts[f] = n
    (out / "FOLDERS-MANIFEST.txt").write_bytes(("\n".join(manifest) + "\n").encode("utf-8"))

    # the base world data (raw and CR-blind)
    lines = ["# sha256 raw, sha256 with every CR removed (the fingerprint is CR-blind), path under the game folder"]
    for fn in WORLD_DATA:
        p = game / "StreamingAssets" / "Data" / "World" / fn
        b = p.read_bytes()
        lines.append(f"{sha(b)} {sha(b.replace(b'\r', b''))} *StreamingAssets/Data/World/{fn}")
    (out / "DATA-WORLD-HASHES.txt").write_bytes(("\n".join(lines) + "\n").encode("ascii"))

    # the check script and the README
    shutil.copy2(CHECK, out / "check-s168.ps1")
    values = {"DATE": a.date, "YYYYMMDD": stamp, "S168_SHA16": a.s168_sha256[:16], "S168_SHA256": a.s168_sha256,
              "S167_SNAPSHOT_TS": a.s167_backup_ts, "S168_BENCH_SUMMARY": a.bench_summary}
    readme = fill_readme(SHEET.read_text(encoding="utf-8"), values)
    (out / "README.md").write_bytes(readme.encode("utf-8"))

    # the zip, one top-level folder like the s167 one
    zp = out.with_suffix(".zip")
    with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
        for root, dirs, files in os.walk(out):
            dirs.sort()
            for fn in sorted(files):
                p = Path(root) / fn
                z.write(p, f"{name}/{p.relative_to(out).as_posix()}")
    with zipfile.ZipFile(zp) as z:
        entries = len(z.namelist())
        bad = z.testzip()
    if bad:
        raise SystemExit(f"zip test failed on {bad}")
    print(f"package: {out}")
    print(f"  dlls 6 + dlls-s167 2 (HASHES.txt {len(hashes)} lines); folders {counts} ({len(manifest)} files)")
    print(f"  zip: {zp} ({entries} entries, {zp.stat().st_size / 1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
