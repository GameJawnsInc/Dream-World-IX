"""Review probe (draft history slice): does os.stat on this Windows/Python see a file another process is writing
(handle still open) at its new size and time, or at the directory entry's old one? _unmoved trusts os.stat."""
import os, subprocess, sys, time
from pathlib import Path

out = Path(__file__).resolve().parents[1] / "out" / "perf" / "review" / "statlag"
out.mkdir(parents=True, exist_ok=True)
f = out / "Block[1][1] Terrain.ff9mesh"
f.write_bytes(b"A" * 4096)
then = time.time_ns() - 60 * 10 ** 9
os.utime(f, ns=(then, then))
st0 = os.stat(f)
child = subprocess.Popen([sys.executable, "-c",
    "import sys,time\n"
    "h=open(sys.argv[1],'r+b'); h.seek(0); h.write(b'B'*4096); h.flush()\n"
    "import os; os.fsync(h.fileno())\n"
    "print('written', flush=True); time.sleep(3)\n", str(f)], stdout=subprocess.PIPE)
child.stdout.readline()
st1 = os.stat(f)
ents = {e.name: e.stat() for e in os.scandir(out)}
e1 = ents[f.name]
print("python", sys.version.split()[0])
print("before  size", st0.st_size, "mtime", st0.st_mtime_ns)
print("open    size", st1.st_size, "mtime", st1.st_mtime_ns, "same-as-before:", (st1.st_size, st1.st_mtime_ns) == (st0.st_size, st0.st_mtime_ns))
print("scandir size", e1.st_size, "mtime", e1.st_mtime_ns, "same-as-before:", (e1.st_size, e1.st_mtime_ns) == (st0.st_size, st0.st_mtime_ns))
child.wait()
st2 = os.stat(f)
print("closed  size", st2.st_size, "mtime", st2.st_mtime_ns, "same-as-before:", (st2.st_size, st2.st_mtime_ns) == (st0.st_size, st0.st_mtime_ns))
print("bytes now B:", f.read_bytes()[:1] == b"B")
