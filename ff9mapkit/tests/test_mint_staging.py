"""stage_mint's ``fbx =`` path must ship the author's FBX byte-verbatim. A custom model may be a
Kaydara *binary* FBX (the Thomas-swap build's case) -- the old implementation round-tripped the file
through an ASCII text decode + newline translation, which corrupts any binary FBX. No install data
needed: the fbx= lane never touches the game bundles."""
from pathlib import Path

from ff9mapkit.models import mint

# A synthetic Kaydara-binary FBX header + bytes no text decode survives: NULs, every byte value
# (0x80+ is invalid ASCII), and bare CR / CRLF runs that newline translation would rewrite.
BINARY_FBX = (b"Kaydara FBX Binary  \x00\x1a\x00" + (7400).to_bytes(4, "little")
              + bytes(range(256)) + b"\r\n\r\r\n\n\x00\xff\xfe")


def test_stage_mint_fbx_is_binary_safe(tmp_path: Path):
    src_dir = tmp_path / "authored"
    src_dir.mkdir()
    (src_dir / "creature.fbx").write_bytes(BINARY_FBX)
    png = b"\x89PNG\r\n\x1a\n" + bytes([0, 255, 13, 10, 26])
    (src_dir / "skin.png").write_bytes(png)

    dest = tmp_path / "Models" / "3" / "6200"
    block = {"id": 6200, "fbx": "creature.fbx", "name": "GEO_MON_B0_M200"}
    man = mint.stage_mint(block, dest, base_dir=src_dir)

    assert man["directive"] == "3DModel 6200 GEO_MON_B0_M200"
    assert (dest / "6200.fbx").read_bytes() == BINARY_FBX     # byte-identical, no decode happened
    assert (dest / "skin.png").read_bytes() == png            # textures ride along untouched
