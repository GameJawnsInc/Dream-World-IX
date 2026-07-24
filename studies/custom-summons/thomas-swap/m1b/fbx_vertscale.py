"""Read the RAW magnitude of the first Geometry's ``Vertices`` array straight out of a binary FBX -- the
numbers Memoria's ModelImporter (geo.GetVertices()) consumes VERBATIM (no unit/axis conversion; the same
verbatim-read law blender_normalize.py documents). This is the authoritative scale check for the s54 hybrid:
the drive writes bones at RAW FF9 units, so the FBX Vertices must be raw-scale too (span ~ the dragon's
~4213-unit skeleton), NOT Blender's reimport object-scale interpretation.

Minimal FBX 7.x binary parser (version 7400): header(27) then nested records; each record =
EndOffset(u32) NumProps(u32) PropsLen(u32) NameLen(u8) Name + properties + nested. Double arrays ('d')
may be zlib-compressed (Encoding==1). We recurse to the first 'Vertices' record and report its bounds.

Run:  py fbx_vertscale.py <file.fbx>
"""
import struct
import sys
import zlib

path = sys.argv[1] if len(sys.argv) > 1 else r"C:/gd/SCRATCH/summon-transplant/thomas_skinned.fbx"
data = open(path, "rb").read()
assert data[:20] == b"Kaydara FBX Binary  ", "not a binary FBX"
version = struct.unpack("<I", data[23:27])[0]
print(f"FBX version {version}")

pos = 27
found = []


def read_property(buf, p):
    t = chr(buf[p]); p += 1
    if t in "YCILFDL":
        sizes = {"Y": 2, "C": 1, "I": 4, "F": 4, "D": 8, "L": 8}
        fmt = {"Y": "<h", "C": "<?", "I": "<i", "F": "<f", "D": "<d", "L": "<q"}[t]
        n = sizes[t]
        val = struct.unpack(fmt, buf[p:p + n])[0]
        return t, val, p + n
    if t in "fdlib":
        length, enc, clen = struct.unpack("<III", buf[p:p + 12]); p += 12
        raw = buf[p:p + clen]; p += clen
        if enc == 1:
            raw = zlib.decompress(raw)
        elem = {"f": ("<f", 4), "d": ("<d", 8), "l": ("<q", 8), "i": ("<i", 4), "b": ("<b", 1)}[t]
        fmt, esz = elem
        vals = struct.unpack("<" + fmt[1] * length, raw) if False else [
            struct.unpack(fmt, raw[i * esz:(i + 1) * esz])[0] for i in range(length)]
        return t, vals, p
    if t in "SR":
        length = struct.unpack("<I", buf[p:p + 4])[0]; p += 4
        val = buf[p:p + length]; p += length
        return t, val, p
    raise ValueError(f"unknown prop type {t!r} at {p}")


def parse_records(buf, start, end, depth, ctx):
    p = start
    while p < end:
        if version >= 7500:
            endoff, numprops, propslen = struct.unpack("<QQQ", buf[p:p + 24]); hp = p + 24
            nl = buf[hp]; hp += 1
        else:
            endoff, numprops, propslen = struct.unpack("<III", buf[p:p + 12]); hp = p + 12
            nl = buf[hp]; hp += 1
        if endoff == 0:
            return p + (25 if version >= 7500 else 13)
        name = buf[hp:hp + nl].decode("ascii", "replace"); hp += nl
        pp = hp
        props = []
        for _ in range(numprops):
            t, v, pp = read_property(buf, pp)
            props.append((t, v))
        # 'Vertices' geometry array
        if name == "Vertices" and props and props[0][0] == "d":
            xs = props[0][1]
            n = len(xs) // 3
            X = xs[0::3]; Y = xs[1::3]; Z = xs[2::3]
            found.append((n, (min(X), max(X)), (min(Y), max(Y)), (min(Z), max(Z))))
        # recurse into nested records (between end of props and endoff)
        nested_start = pp
        if nested_start < endoff:
            parse_records(buf, nested_start, endoff, depth + 1, name)
        p = endoff
    return p


parse_records(data, pos, len(data), 0, "root")

if not found:
    print("no Vertices array found")
    sys.exit(1)
for i, (n, xb, yb, zb) in enumerate(found):
    span = (xb[1] - xb[0], yb[1] - yb[0], zb[1] - zb[0])
    print(f"Geometry #{i}: {n} verts")
    print(f"  X [{xb[0]:.1f}, {xb[1]:.1f}]  Y [{yb[0]:.1f}, {yb[1]:.1f}]  Z [{zb[0]:.1f}, {zb[1]:.1f}]")
    print(f"  span = ({span[0]:.1f}, {span[1]:.1f}, {span[2]:.1f})  max={max(span):.1f}")
    verdict = ("RAW (~thousands, matches the ~4213u skeleton)" if 500 < max(span) < 50000
               else "OUT OF EXPECTED RAW BAND -- CHECK SCALE")
    print(f"  verdict: {verdict}")
