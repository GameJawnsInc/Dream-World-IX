"""SimpleJSON binary codec -- the format Memoria's JSONNode.Serialize/Deserialize use for the unencrypted
per-slot extra save file (SavedData_ww_Memoria_*.dat), the load-authoritative store the #5 item/equip/gil
editor must write. These tests pin the byte format against the C# BinaryWriter spec (tags Int32 LE; strings
.NET 7-bit-length-prefixed UTF-8; tagged leaves), the round-trip fidelity (unchanged tree re-serializes
byte-identically), the ordered-map + path helpers, and -- install-gated -- a real on-disk extra file.
"""
from __future__ import annotations

import glob
import os
import struct

import pytest

from ff9mapkit import sjbinary as SJ


# ---- 7-bit (LEB128) length prefix -------------------------------------------------------------
@pytest.mark.parametrize("n", [0, 1, 5, 127, 128, 200, 16383, 16384, 1_000_000])
def test_7bit_roundtrip(n):
    import io
    w = io.BytesIO()
    SJ._write_7bit(w, n)
    r = io.BytesIO(w.getvalue())
    assert SJ._read_7bit(r) == n


def test_7bit_known_encodings():
    import io
    def enc(n):
        w = io.BytesIO(); SJ._write_7bit(w, n); return w.getvalue()
    assert enc(0) == b"\x00"
    assert enc(127) == b"\x7f"
    assert enc(128) == b"\x80\x01"        # .NET Write7BitEncodedInt
    assert enc(200) == b"\xc8\x01"


# ---- byte-exact format (pins the C# layout) ---------------------------------------------------
def test_class_with_int_leaf_exact_bytes():
    # root Class { "gil": IntValue 500 } -- the exact bytes C# BinaryWriter would emit
    root = SJ.SJClass()
    root.add("gil", SJ.SJData(SJ.INT, 500))
    expected = (
        struct.pack("<i", SJ.CLASS) +     # 02 00 00 00  Class tag
        struct.pack("<i", 1) +            # 01 00 00 00  one key
        b"\x03gil" +                      # 7-bit len 3 + "gil"
        struct.pack("<i", SJ.INT) +       # 04 00 00 00  IntValue tag
        struct.pack("<i", 500)            # f4 01 00 00  value 500
    )
    assert SJ.dumps(root) == expected


def test_string_value_leaf_exact_bytes():
    root = SJ.SJClass()
    root.add("name", SJ.SJData(SJ.VALUE, "Zidane"))
    expected = (struct.pack("<i", SJ.CLASS) + struct.pack("<i", 1)
                + b"\x04name" + struct.pack("<i", SJ.VALUE) + b"\x06Zidane")
    assert SJ.dumps(root) == expected


def test_array_of_classes_exact_bytes():
    # items = [ {id:236, count:7} ] -- an inventory entry shape (note: real saves alpha-sort main-block keys,
    # but the EXTRA file's class keys are insertion-order, which we preserve verbatim)
    entry = SJ.SJClass(); entry.add("id", SJ.SJData(SJ.INT, 236)); entry.add("count", SJ.SJData(SJ.INT, 7))
    arr = SJ.SJArray([entry])
    expected = (
        struct.pack("<i", SJ.ARRAY) + struct.pack("<i", 1)
        + struct.pack("<i", SJ.CLASS) + struct.pack("<i", 2)
        + b"\x02id" + struct.pack("<i", SJ.INT) + struct.pack("<i", 236)
        + b"\x05count" + struct.pack("<i", SJ.INT) + struct.pack("<i", 7)
    )
    assert SJ.dumps(arr) == expected


# ---- leaf type fidelity -----------------------------------------------------------------------
def test_all_leaf_tags_roundtrip():
    root = SJ.SJClass()
    root.add("i", SJ.SJData(SJ.INT, -12345))
    root.add("d", SJ.SJData(SJ.DOUBLE, 3.141592653589793))
    root.add("f", SJ.SJData(SJ.FLOAT, 1.5))            # 1.5 is exact in float32
    root.add("b0", SJ.SJData(SJ.BOOL, False))
    root.add("b1", SJ.SJData(SJ.BOOL, True))
    root.add("s", SJ.SJData(SJ.VALUE, "hello ☃"))  # non-ASCII -> UTF-8
    back, trailing = SJ.loads(SJ.dumps(root))
    assert trailing == b""
    assert back.get("i").value == -12345
    assert back.get("d").value == 3.141592653589793
    assert back.get("f").value == 1.5
    assert back.get("b0").value is False and back.get("b1").value is True
    assert back.get("s").value == "hello ☃"
    # tags preserved
    assert [back.get(k).tag for k in ("i", "d", "f", "b0", "s")] == [SJ.INT, SJ.DOUBLE, SJ.FLOAT, SJ.BOOL, SJ.VALUE]


def test_float_bit_exact():
    # a float32 read -> python float -> re-packed as Single is bit-identical (lossless widen/narrow)
    raw_single = struct.pack("<f", 0.10000000149011612)
    root = SJ.SJArray([SJ.SJData(SJ.FLOAT, struct.unpack("<f", raw_single)[0])])
    assert SJ.dumps(root) == struct.pack("<i", SJ.ARRAY) + struct.pack("<i", 1) + struct.pack("<i", SJ.FLOAT) + raw_single


# ---- ordered map + mutation -------------------------------------------------------------------
def test_class_preserves_key_order():
    root = SJ.SJClass()
    for k in ("z", "a", "m", "00001_time"):
        root.add(k, SJ.SJData(SJ.INT, 1))
    assert root.keys() == ["z", "a", "m", "00001_time"]      # insertion order, NOT sorted
    back, _ = SJ.loads(SJ.dumps(root))
    assert back.keys() == ["z", "a", "m", "00001_time"]      # survives a round-trip


def test_set_in_place_keeps_order_and_is_byte_stable():
    root = SJ.SJClass()
    root.add("gil", SJ.SJData(SJ.INT, 500))
    root.add("other", SJ.SJData(SJ.VALUE, "keep"))
    before = SJ.dumps(root)
    root.set("gil", SJ.SJData(SJ.INT, 500))                  # same value -> identical bytes
    assert SJ.dumps(root) == before
    root.set("gil", SJ.SJData(SJ.INT, 12345))               # changed value
    after = SJ.dumps(root)
    assert after != before
    assert SJ.loads(after)[0].get("gil").value == 12345
    assert SJ.loads(after)[0].keys() == ["gil", "other"]    # order + sibling preserved


def test_set_unknown_key_raises():
    root = SJ.SJClass()
    root.add("gil", SJ.SJData(SJ.INT, 1))
    with pytest.raises(KeyError):
        root.set("nope", SJ.SJData(SJ.INT, 2))


def test_get_path():
    inner = SJ.SJClass(); inner.add("equip", SJ.SJArray([SJ.SJData(SJ.INT, 1), SJ.SJData(SJ.INT, 112)]))
    players = SJ.SJArray([inner])
    common = SJ.SJClass(); common.add("players", players); common.add("gil", SJ.SJData(SJ.INT, 999))
    root = SJ.SJClass(); root.add("40000_Common", common)
    assert SJ.get_path(root, "40000_Common", "gil").value == 999
    assert SJ.get_path(root, "40000_Common", "players", 0, "equip", 1).value == 112
    assert SJ.get_path(root, "40000_Common", "missing") is None
    assert SJ.get_path(root, "40000_Common", "players", 9) is None     # index out of range
    assert SJ.get_path(root, "40000_Common", "gil", "x") is None       # descend into a leaf


def test_trailing_bytes_preserved():
    root = SJ.SJClass(); root.add("a", SJ.SJData(SJ.INT, 1))
    blob = SJ.dumps(root) + b"\xde\xad\xbe\xef"
    back, trailing = SJ.loads(blob)
    assert trailing == b"\xde\xad\xbe\xef"
    assert SJ.dumps(back, trailing) == blob


def test_unknown_tag_raises():
    bad = struct.pack("<i", 99)
    with pytest.raises(ValueError):
        SJ.loads(bad)


# ---- install-gated: the real extra file round-trips byte-identical -----------------------------
def _real_extra_files():
    from ff9mapkit import save as S
    d = S.default_save_dir()
    if not d:
        return []
    return sorted(glob.glob(os.path.join(str(d), "SavedData_ww_Memoria_*.dat")))


@pytest.mark.skipif(not _real_extra_files(), reason="no real Memoria extra save on this machine")
def test_real_extra_file_roundtrip_byte_identical():
    for path in _real_extra_files():
        raw = open(path, "rb").read()
        root, trailing = SJ.loads(raw)
        assert SJ.dumps(root, trailing) == raw, f"round-trip mismatch: {os.path.basename(path)}"
        # sanity: the item/equip/gil surface is present in the first tree
        assert SJ.get_path(root, "40000_Common", "gil") is not None
        assert SJ.get_path(root, "40000_Common", "players") is not None
