"""Read the float64/float32 constants the RotMatrix builders + matmul use, to confirm the
angle->radian scale is 2*pi/4096 and the fixed-point factors are 4096. Read-only DLL."""
from __future__ import annotations
import struct, sys, math
from pathlib import Path
_DISASM = Path(__file__).resolve().parents[2] / "disasm"
sys.path.insert(0, str(_DISASM))
import refkit  # noqa

pe = refkit.load("x64")
base = refkit.image_base(pe)

def f64(rva):
    return struct.unpack("<d", refkit.read_rva(pe, rva, 8))[0]
def f32(rva):
    return struct.unpack("<f", refkit.read_rva(pe, rva, 4))[0]

# builder chain: xmm7 = angle; *= C1(0x4b688); *= C2(0x4b6b8); *= C3(0x4b6a0); /= C4(0x4b6b0)
C1 = f64(0x4b688); C2 = f64(0x4b6b8); C3 = f64(0x4b6a0); C4 = f64(0x4b6b0)
net = C1 * C2 * C3 / C4
print(f"builder angle-scale constants:")
print(f"  C1@0x4b688 = {C1!r}")
print(f"  C2@0x4b6b8 = {C2!r}")
print(f"  C3@0x4b6a0 = {C3!r}")
print(f"  C4@0x4b6b0 = {C4!r}")
print(f"  net = C1*C2*C3/C4 = {net!r}")
print(f"  2*pi/4096         = {2*math.pi/4096!r}")
print(f"  match 2pi/4096? {abs(net - 2*math.pi/4096) < 1e-15}")

# fixed-point factor applied to cos/sin before cvttsd2si (0x4b6c8), and the matmul /divisor (0x4b6d8)
FP = f64(0x4b6c8)
DIV = f32(0x4b6d8)
print(f"\n  fixed-point *factor @0x4b6c8 (f64) = {FP!r}   (expect 4096.0)")
print(f"  matmul /divisor    @0x4b6d8 (f32) = {DIV!r}   (expect 4096.0)")
