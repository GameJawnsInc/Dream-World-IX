"""The Memoria EXTRA-save decoder (``save.read_extra_tree`` / ``read_extra_vectors``).

The extra file is SimpleJSON's BINARY serialization, not text -- the synthetic files here are written
with a port of the engine's own ``Serialize`` methods (JSONClass/JSONArray/JSONData), so a decoder that
agreed only with itself could not pass. No crypto: the extra file is unencrypted, so unlike
test_save.py this module does not skip without pycryptodome."""
import struct

from ff9mapkit import save as S


# --- a port of SimpleJSON's binary writer (JSONClass.cs:202 / JSONArray.cs:132 / JSONData.cs:55) ---
def _str(s: str) -> bytes:
    raw = s.encode("utf-8")
    n, out = len(raw), bytearray()
    while True:                               # BinaryWriter.Write(string): 7-bit length prefix
        b = n & 0x7F
        n >>= 7
        out.append(b | (0x80 if n else 0))
        if not n:
            break
    return bytes(out) + raw


def _ser(node) -> bytes:
    if isinstance(node, dict):
        body = b"".join(_str(k) + _ser(v) for k, v in node.items())
        return struct.pack("<ii", 2, len(node)) + body
    if isinstance(node, list):
        return struct.pack("<ii", 1, len(node)) + b"".join(_ser(v) for v in node)
    if isinstance(node, bool):
        return struct.pack("<i?", 6, node)
    if isinstance(node, int):                 # a numeric string that round-trips AsInt -> tag 4
        return struct.pack("<ii", 4, node)
    if isinstance(node, float):
        return struct.pack("<id", 5, node)
    return struct.pack("<i", 3) + _str(str(node))


def _extra(vectors, *, geg_b64="AAAA", time=12.5, dictionaries=()):
    return {
        "95000_Setting": {"00001_time": time},
        "20000_Event": {
            "gStepCount": 0,
            "gEventGlobal": geg_b64,
            "gAbilityUsage": [],
            "gScriptVector": [{"id": vid, "entries": cells} for vid, cells in vectors.items()],
            "gScriptDictionary": list(dictionaries),
        },
        "40000_Common": {},
    }


def test_decodes_vectors_including_a_const4_id_and_negative_cells(tmp_path):
    p = tmp_path / "SavedData_ww_Memoria_Autosave.dat"
    p.write_bytes(_ser(_extra({4242: [1001, -7, 4011], 8400000: [424242, 17]})))
    assert S.read_extra_vectors(p) == {4242: [1001, -7, 4011], 8400000: [424242, 17]}


def test_the_tree_keeps_every_section(tmp_path):
    p = tmp_path / "x.dat"
    p.write_bytes(_ser(_extra({}, time=3.25)))
    tree = S.read_extra_tree(p)
    assert list(tree) == ["95000_Setting", "20000_Event", "40000_Common"]
    assert tree["95000_Setting"]["00001_time"] == 3.25
    assert tree["20000_Event"]["gScriptVector"] == []


def test_a_stale_tail_from_a_longer_older_file_is_ignored(tmp_path):
    # SaveToFile uses File.OpenWrite, which does not truncate: a shorter save leaves the old tail.
    p = tmp_path / "x.dat"
    fresh = _ser(_extra({7: [1]}))
    p.write_bytes(fresh + b"\x04\x00\x00\x00GARBAGE-FROM-AN-OLDER-LONGER-SAVE" * 3)
    assert S.read_extra_vectors(p) == {7: [1]}


def test_an_absent_file_is_none_not_empty(tmp_path):
    # None ("no extra file at all") and {} ("a file with no vectors") are different verdicts.
    assert S.read_extra_tree(tmp_path / "nope.dat") is None
    assert S.read_extra_vectors(tmp_path / "nope.dat") is None
    p = tmp_path / "empty.dat"
    p.write_bytes(_ser(_extra({})))
    assert S.read_extra_vectors(p) == {}


def test_a_multibyte_length_prefix_decodes(tmp_path):
    long_key = "k" * 200                      # > 127 bytes -> a two-byte 7-bit length prefix
    p = tmp_path / "x.dat"
    p.write_bytes(_ser({long_key: "v", "20000_Event": {"gScriptVector": [{"id": 1, "entries": [5]}]}}))
    assert S.read_extra_tree(p)[long_key] == "v"
    assert S.read_extra_vectors(p) == {1: [5]}


def test_an_unknown_tag_is_a_loud_error_not_a_silent_empty(tmp_path):
    import pytest
    p = tmp_path / "x.dat"
    p.write_bytes(struct.pack("<i", 99))
    with pytest.raises(ValueError, match="unknown SimpleJSON binary tag 99"):
        S.read_extra_tree(p)


def test_gEventGlobal_still_found_by_the_existing_byte_scanner(tmp_path):
    # read_extra_gEventGlobal scans raw bytes for the 2732-char Base64 run; it must keep working on
    # the binary container (the string is stored verbatim after its length prefix).
    import base64
    geg = bytes(range(256)) * 8
    p = tmp_path / "x.dat"
    p.write_bytes(_ser(_extra({}, geg_b64=base64.b64encode(geg).decode())))
    assert S.read_extra_gEventGlobal(p) == geg
    assert base64.b64decode(S.read_extra_tree(p)["20000_Event"]["gEventGlobal"]) == geg
