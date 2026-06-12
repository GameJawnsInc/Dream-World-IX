"""SimpleJSON BINARY codec -- the format Memoria's ``JSONNode.Serialize`` / ``JSONNode.Deserialize`` use for
the unencrypted per-slot extra save file ``SavedData_ww_Memoria_{slot}_{save}.dat``.

This is the foundation for the #5 save-side item/equipment/gil editor: the extra file is what the game LOADS
(it overrides the encrypted main block -- memory project-ff9-save-item-layout), and it stores items/equip/gil
as a nested SimpleJSON tree, so editing it needs a real parse -> mutate -> re-serialize, NOT an in-place byte
patch. This module is the parse/serialize half; the editor (a separate ``save_items`` surface) layers on top.

Byte-exact with C# ``BinaryWriter`` (verified by a round-trip test against the real file):

* tags + counts are **Int32 LE** (``BinaryWriter.Write((int)...)``);
* strings are **.NET 7-bit-length-prefixed UTF-8** (``BinaryWriter.Write(string)`` / ``BinaryReader.ReadString``):
  a 7-bit-encoded (LEB128) BYTE length then the UTF-8 bytes;
* leaves are tagged: ``Value=3`` string, ``IntValue=4`` Int32, ``DoubleValue=5`` Double, ``BoolValue=6`` Bool
  (1 byte), ``FloatValue=7`` Single. (``Array=1`` = count + children; ``Class=2`` = count + key/value pairs.)

★ FIDELITY: ``JSONData.Serialize`` RE-INFERS a leaf's tag from its string value on every write (int->4, float->7,
double->5, bool->6, else string->3). We instead **preserve each leaf's READ tag** -- which already equals what
re-inference produces, because C# wrote the on-disk file via that same inference (so no Value(3) on disk ever
holds a parseable number). Preserving the read tag + the ordered keys means an UNCHANGED tree re-serializes
byte-for-byte identically; we never reproduce C#'s float/culture formatting. A changed int leaf emits ``IntValue``
(tag 4) -- exactly what C# does for an int.
"""
from __future__ import annotations

import io
import struct

# JSONBinaryTag (SimpleJSON/JSONBinaryTag.cs)
ARRAY = 1
CLASS = 2
VALUE = 3            # string
INT = 4             # Int32
DOUBLE = 5
BOOL = 6
FLOAT = 7           # Single


class SJData:
    """A leaf node: a tag (VALUE/INT/DOUBLE/BOOL/FLOAT) + its typed Python value (str/int/float/bool)."""
    __slots__ = ("tag", "value")

    def __init__(self, tag: int, value):
        self.tag = tag
        self.value = value

    def __repr__(self):
        return f"SJData(tag={self.tag}, value={self.value!r})"


class SJArray:
    """An ordered list of child nodes (JSONArray)."""
    __slots__ = ("items",)

    def __init__(self, items=None):
        self.items = list(items) if items is not None else []

    def __len__(self):
        return len(self.items)

    def __iter__(self):
        return iter(self.items)

    def __repr__(self):
        return f"SJArray({len(self.items)} items)"


class SJClass:
    """An ORDERED string->node map (JSONClass). Key order is preserved (C# Dictionary iterates in insertion
    order for an add-only save tree), which is what makes an unchanged re-serialize byte-identical."""
    __slots__ = ("_items", "_idx")

    def __init__(self):
        self._items: list = []          # [(key, node), ...] in on-disk order
        self._idx: dict = {}            # key -> index in _items

    def add(self, key: str, node) -> None:
        """Append a key/node in order (used by the parser; a duplicate key replaces in place, mirroring a dict)."""
        if key in self._idx:
            self._items[self._idx[key]] = (key, node)
        else:
            self._idx[key] = len(self._items)
            self._items.append((key, node))

    def get(self, key: str):
        i = self._idx.get(key)
        return self._items[i][1] if i is not None else None

    def set(self, key: str, node) -> None:
        """Replace an existing key's node in place (keeps order). Raises KeyError if the key is absent (the
        editor only mutates existing leaves -- adding a new key would change the layout)."""
        if key not in self._idx:
            raise KeyError(f"key {key!r} not in this SJClass (keys: {list(self._idx)})")
        i = self._idx[key]
        self._items[i] = (key, node)

    def keys(self):
        return [k for k, _ in self._items]

    def __contains__(self, key):
        return key in self._idx

    def __iter__(self):
        return iter(self._items)                       # (key, node) pairs, in order

    def __len__(self):
        return len(self._items)

    def __repr__(self):
        return f"SJClass(keys={self.keys()})"


# --- low-level .NET BinaryReader/Writer primitives ------------------------------------------------

def _read_7bit(r) -> int:
    """.NET ``Read7BitEncodedInt`` -- LEB128 unsigned (low 7 bits per byte, high bit = continue)."""
    val = 0
    shift = 0
    while True:
        b = r.read(1)
        if not b:
            raise ValueError("unexpected EOF reading a 7-bit length")
        b = b[0]
        val |= (b & 0x7F) << shift
        if not (b & 0x80):
            return val
        shift += 7
        if shift > 35:
            raise ValueError("7-bit length too long (corrupt stream)")


def _write_7bit(w, n: int) -> None:
    if n < 0:
        raise ValueError("string length cannot be negative")
    while n >= 0x80:
        w.write(bytes([(n & 0x7F) | 0x80]))
        n >>= 7
    w.write(bytes([n]))


def _read_string(r) -> str:
    n = _read_7bit(r)
    raw = r.read(n)
    if len(raw) != n:
        raise ValueError(f"unexpected EOF reading a {n}-byte string")
    return raw.decode("utf-8")


def _write_string(w, s: str) -> None:
    raw = s.encode("utf-8")
    _write_7bit(w, len(raw))
    w.write(raw)


def _read_i32(r) -> int:
    raw = r.read(4)
    if len(raw) != 4:
        raise ValueError("unexpected EOF reading an Int32")
    return struct.unpack("<i", raw)[0]


def _write_i32(w, v: int) -> None:
    w.write(struct.pack("<i", v))


# --- tree (de)serialization (mirrors JSONNode.Deserialize / *.Serialize) --------------------------

def _deserialize(r):
    tag = _read_i32(r)
    if tag == ARRAY:
        n = _read_i32(r)
        return SJArray([_deserialize(r) for _ in range(n)])
    if tag == CLASS:
        n = _read_i32(r)
        c = SJClass()
        for _ in range(n):
            key = _read_string(r)
            c.add(key, _deserialize(r))
        return c
    if tag == VALUE:
        return SJData(VALUE, _read_string(r))
    if tag == INT:
        return SJData(INT, _read_i32(r))
    if tag == DOUBLE:
        return SJData(DOUBLE, struct.unpack("<d", r.read(8))[0])
    if tag == BOOL:
        return SJData(BOOL, r.read(1)[0] != 0)
    if tag == FLOAT:
        return SJData(FLOAT, struct.unpack("<f", r.read(4))[0])
    raise ValueError(f"unknown SimpleJSON tag {tag} at offset {r.tell() - 4}")


def _serialize(node, w) -> None:
    if isinstance(node, SJArray):
        _write_i32(w, ARRAY)
        _write_i32(w, len(node.items))
        for it in node.items:
            _serialize(it, w)
    elif isinstance(node, SJClass):
        _write_i32(w, CLASS)
        _write_i32(w, len(node._items))
        for key, child in node._items:
            _write_string(w, key)
            _serialize(child, w)
    elif isinstance(node, SJData):
        _write_i32(w, node.tag)
        if node.tag == VALUE:
            _write_string(w, node.value)
        elif node.tag == INT:
            _write_i32(w, int(node.value))
        elif node.tag == DOUBLE:
            w.write(struct.pack("<d", float(node.value)))
        elif node.tag == BOOL:
            w.write(b"\x01" if node.value else b"\x00")
        elif node.tag == FLOAT:
            w.write(struct.pack("<f", float(node.value)))
        else:
            raise ValueError(f"cannot serialize leaf with tag {node.tag}")
    else:
        raise TypeError(f"not an SJ node: {type(node).__name__}")


# --- public API -----------------------------------------------------------------------------------

def loads(data: bytes):
    """Parse the SimpleJSON-binary ``data`` into a node tree. Returns ``(root, trailing)`` -- ``trailing`` is
    any bytes after the single root tree (normally empty; preserved so a re-emit is byte-exact even if Memoria
    ever pads the file)."""
    r = io.BytesIO(data)
    root = _deserialize(r)
    trailing = r.read()
    return root, trailing


def dumps(root, trailing: bytes = b"") -> bytes:
    """Serialize ``root`` (+ any preserved ``trailing`` bytes) back to SimpleJSON-binary bytes."""
    w = io.BytesIO()
    _serialize(root, w)
    w.write(trailing)
    return w.getvalue()


def get_path(root, *keys):
    """Walk a path of string keys (SJClass) / int indices (SJArray) and return the node, or ``None`` if any
    step is missing. e.g. ``get_path(root, "40000_Common", "players", 0, "equip")``."""
    node = root
    for k in keys:
        if isinstance(k, int) and isinstance(node, SJArray):
            if k < 0 or k >= len(node.items):
                return None
            node = node.items[k]
        elif isinstance(node, SJClass):
            node = node.get(k)
        else:
            return None
        if node is None:
            return None
    return node


def diff_paths(a, b, _prefix=()):
    """Yield the path (a tuple of string keys / int indices) of every spot where trees ``a`` and ``b`` differ.
    A *structural* difference -- a different node type, a different SJClass key list, or a different SJArray
    length -- yields the path of the differing node ITSELF and does not recurse into it; otherwise recursion
    continues and differing leaves yield their own path. Used to VERIFY a save edit is scoped: an edit may only
    touch paths under a known prefix (e.g. ``("40000_Common","items")``); anything else changing => abort."""
    if type(a) is not type(b):
        yield _prefix
        return
    if isinstance(a, SJData):
        if a.tag != b.tag or a.value != b.value:
            yield _prefix
    elif isinstance(a, SJArray):
        if len(a.items) != len(b.items):
            yield _prefix                                  # a length change => the array itself changed
        else:
            for i, (x, y) in enumerate(zip(a.items, b.items)):
                yield from diff_paths(x, y, _prefix + (i,))
    elif isinstance(a, SJClass):
        if a.keys() != b.keys():
            yield _prefix                                  # a key added/removed/reordered => the class changed
        else:
            for k, _ in a._items:
                yield from diff_paths(a.get(k), b.get(k), _prefix + (k,))
    # any other type: treated as equal (the tree only holds SJData/SJArray/SJClass)
