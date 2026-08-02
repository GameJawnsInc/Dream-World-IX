"""Restore the pristine bench from the byte-verified backup (pre-apron-carry)."""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, r"C:\gd\Dream-World-IX\.claude\worktrees\angry-williamson-08e8bb\studies\path-d-new-world")
from terrace_wall_strip import load_bench                   # noqa: E402

BK = Path(r"C:\gd\Dream-World-IX\backups\terrace-strip-prewall.20260731-220001")
assert BK.is_dir(), BK

tris, bms = load_bench()
live = {p.name: p for (p, _bm) in bms.values()}
n = 0
for f in sorted(BK.iterdir()):
    dst = live.get(f.name)
    assert dst is not None, f"no live file for backup {f.name}"
    src_b = f.read_bytes()
    if dst.read_bytes() == src_b:
        print(f"identical  {f.name}")
        continue
    shutil.copy2(f, dst)
    assert dst.read_bytes() == src_b, f"VERIFY FAILED {f.name}"
    print(f"restored   {f.name} ({len(src_b)} bytes, verified)")
    n += 1
print(f"done: {n} files restored, {len(live)} bench files total")
