"""fsutil: the atomic-write helpers every load-bearing writer routes through."""

from ff9mapkit import fsutil


def test_atomic_write_bytes_roundtrip_and_no_tmp_left(tmp_path):
    p = tmp_path / "out.bin"
    fsutil.atomic_write_bytes(p, b"\x00\x01")
    assert p.read_bytes() == b"\x00\x01"
    fsutil.atomic_write_bytes(p, b"\x02")          # overwrite replaces wholesale
    assert p.read_bytes() == b"\x02"
    assert not p.with_name(p.name + ".tmp").exists()


def test_atomic_write_text_matches_path_write_text(tmp_path):
    a = tmp_path / "a.txt"
    b = tmp_path / "b.txt"
    a.write_text("x\ny\n", encoding="utf-8")
    fsutil.atomic_write_text(b, "x\ny\n", encoding="utf-8")
    assert b.read_bytes() == a.read_bytes()        # drop-in: identical newline translation
    assert not b.with_name(b.name + ".tmp").exists()
