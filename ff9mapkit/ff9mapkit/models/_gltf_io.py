"""Coordinate-INDEPENDENT glTF 2.0 building blocks: a binary-buffer/accessor builder + a .glb writer, and
the FF9 legacy-AnimationClip reader (raw Unity values; the Unity->glTF coordinate conversion is applied by
the caller at emit time). Kept separate from the (convention-bearing) exporter so this half stays purely
mechanical + easily unit-tested.
"""
from __future__ import annotations

import json
import struct

# glTF accessor component types
FLOAT = 5126
UNSIGNED_INT = 5125
UNSIGNED_SHORT = 5123
# bufferView targets
ARRAY_BUFFER = 34962          # vertex attributes
ELEMENT_ARRAY_BUFFER = 34963  # indices


class GltfBuffer:
    """Accumulate binary data into one buffer + emit the bufferViews/accessors that reference it.

    Each ``add_*`` packs a flat value list, 4-byte-aligns it, appends a bufferView, and appends an accessor,
    returning the accessor index (what the glTF mesh/skin/animation nodes reference)."""

    def __init__(self):
        self.blob = bytearray()
        self.bufferViews: list = []
        self.accessors: list = []

    def _align(self):
        while len(self.blob) % 4:
            self.blob.append(0)

    def _view(self, data: bytes, target=None) -> int:
        self._align()
        offset = len(self.blob)
        self.blob += data
        view = {"buffer": 0, "byteOffset": offset, "byteLength": len(data)}
        if target is not None:
            view["target"] = target
        self.bufferViews.append(view)
        return len(self.bufferViews) - 1

    def add(self, values, comp_type: int, gltf_type: str, *, target=None, minmax=False) -> int:
        """values = flat list; gltf_type in {SCALAR,VEC2,VEC3,VEC4,MAT4}. Returns the accessor index."""
        ncomp = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}[gltf_type]
        count = len(values) // ncomp
        fmt = {FLOAT: "<%df", UNSIGNED_INT: "<%dI", UNSIGNED_SHORT: "<%dH"}[comp_type]
        data = struct.pack(fmt % len(values), *values)
        view = self._view(data, target=target)
        acc = {"bufferView": view, "componentType": comp_type, "count": count, "type": gltf_type}
        if minmax and count:
            cols = [values[i::ncomp] for i in range(ncomp)]
            acc["min"] = [min(c) for c in cols]
            acc["max"] = [max(c) for c in cols]
        self.accessors.append(acc)
        return len(self.accessors) - 1


def write_glb(gltf: dict, blob: bytes, path) -> None:
    """Serialize a glTF dict + its single binary buffer as a .glb (one self-contained file Blender opens)."""
    gltf = dict(gltf)
    gltf.setdefault("asset", {"version": "2.0", "generator": "ff9mapkit"})
    gltf["buffers"] = [{"byteLength": len(blob)}]
    json_bytes = json.dumps(gltf, separators=(",", ":")).encode("utf-8")
    json_pad = (4 - len(json_bytes) % 4) % 4
    json_bytes += b" " * json_pad
    bin_pad = (4 - len(blob) % 4) % 4
    bin_bytes = bytes(blob) + b"\x00" * bin_pad
    total = 12 + 8 + len(json_bytes) + 8 + len(bin_bytes)
    with open(path, "wb") as f:
        f.write(struct.pack("<III", 0x46546C67, 2, total))                 # 'glTF', version 2, total len
        f.write(struct.pack("<II", len(json_bytes), 0x4E4F534A))           # JSON chunk header ('JSON')
        f.write(json_bytes)
        f.write(struct.pack("<II", len(bin_bytes), 0x004E4942))            # BIN chunk header ('BIN\0')
        f.write(bin_bytes)


# --------------------------------------------------------------------- glTF READER (the return path)

_READ_FMT = {5126: ("f", 4), 5125: ("I", 4), 5123: ("H", 2), 5121: ("B", 1), 5122: ("h", 2), 5120: ("b", 1)}
_READ_NC = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}
_NORM_DENOM = {5121: 255.0, 5123: 65535.0, 5120: 127.0, 5122: 32767.0}


def read_glb(path) -> tuple:
    """Parse a ``.glb`` (or a ``.gltf`` + external/embedded ``.bin``) -> (gltf_dict, binary_blob)."""
    data = open(path, "rb").read()
    if data[:4] == b"glTF":                                  # binary container
        _magic, _ver, _total = struct.unpack_from("<III", data, 0)
        jlen, _jtype = struct.unpack_from("<II", data, 12)
        gltf = json.loads(data[20:20 + jlen].decode("utf-8"))
        blob, off = b"", 20 + jlen
        while off + 8 <= len(data):
            clen, ctype = struct.unpack_from("<II", data, off)
            if ctype == 0x004E4942:                          # 'BIN\0'
                blob = data[off + 8: off + 8 + clen]
            off += 8 + clen
        return gltf, blob
    gltf = json.loads(data.decode("utf-8"))                  # JSON .gltf
    buf = (gltf.get("buffers") or [{}])[0]
    uri = buf.get("uri", "")
    if uri.startswith("data:"):
        import base64
        blob = base64.b64decode(uri.split(",", 1)[1])
    elif uri:
        from urllib.parse import unquote
        from pathlib import Path as _P
        blob = open(_P(path).parent / unquote(uri), "rb").read()
    else:
        blob = b""
    return gltf, blob


def decode_accessor(gltf: dict, blob: bytes, index: int) -> list:
    """Accessor index -> list of component tuples (respects byteStride, componentType, and `normalized`).
    Raises on a sparse accessor (Blender rarely emits it) so a bad re-export fails loud, not silent."""
    a = gltf["accessors"][index]
    if "sparse" in a:
        raise ValueError("glTF sparse accessor is unsupported -- re-export from Blender without sparse")
    bv = gltf["bufferViews"][a["bufferView"]]
    base = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
    fmt, sz = _READ_FMT[a["componentType"]]
    nc = _READ_NC[a["type"]]
    stride = bv.get("byteStride") or nc * sz
    denom = _NORM_DENOM.get(a["componentType"], 1.0) if a.get("normalized") else 1.0
    out = []
    for i in range(a["count"]):
        vals = struct.unpack_from("<%d%s" % (nc, fmt), blob, base + i * stride)
        out.append(tuple(v / denom for v in vals) if denom != 1.0 else vals)
    return out


# --------------------------------------------------------------------- animation clip reader

def _kf(k, ncomp):
    """A Unity keyframe {time, value{x,y,z[,w]}} -> (time, (v0..v_{n-1}))."""
    v = k["value"]
    comps = ("x", "y", "z", "w")[:ncomp]
    return float(k["time"]), tuple(float(v[c]) for c in comps)


def read_clip(bundle, geo_id: int, anim_key: int) -> "dict | None":
    """Read a legacy AnimationClip (``animations/{geo_id}/{anim_key}.anim`` in p0data5) into RAW Unity curves:

        {"name", "sample_rate", "length",
         "bones": {bonePath: {"rot": [(t,(x,y,z,w))...], "pos": [(t,(x,y,z))...], "scale": [(t,(x,y,z))...]}}}

    Rotation is a quaternion curve (Unity ``m_RotationCurves``), position/scale are vec3 curves; each keys by
    the bone's hierarchy PATH ("bone000/bone001/..."). No coordinate conversion here -- the caller flips to
    glTF handedness. Returns None if the clip isn't found. ``bundle`` is a loaded p0data5 (see gltf.py)."""
    want = f"animations/{geo_id}/{anim_key}.anim"
    pptr = None
    for k, p in bundle.container.items():
        if p.type.name == "AnimationClip" and want in k.lower():
            pptr = p
            break
    if pptr is None:
        return None
    tt = pptr.read_typetree()
    bones: dict = {}

    def bone_num(path):
        seg = path.split("/")[-1]
        return int(seg[4:]) if seg.startswith("bone") and seg[4:].isdigit() else None

    def collect(curve_field, chan, ncomp):
        for c in tt.get(curve_field, []) or []:
            path = c.get("path")
            keys = (c.get("curve") or {}).get("m_Curve", []) or []
            if not path or not keys:
                continue
            bones.setdefault(path, {"bone": bone_num(path)})[chan] = [_kf(k, ncomp) for k in keys]

    collect("m_RotationCurves", "rot", 4)
    collect("m_PositionCurves", "pos", 3)
    collect("m_ScaleCurves", "scale", 3)
    length = max((t for b in bones.values() for chan in ("rot", "pos", "scale") if chan in b
                  for t, _ in b[chan]), default=0.0)
    return {"name": tt.get("m_Name"), "sample_rate": float(tt.get("m_SampleRate", 30.0)),
            "length": length, "bones": bones}
