"""Review probe (kernels slice): a truncated .ff9mesh through read_ff9mesh's two lanes (fd635112).

The struct lane (the code before fd635112, and a kit without numpy today) raises struct.error on a file shorter than
its header's channels; the numpy lane raises ValueError("buffer is smaller than requested size"). coastnav._Loader
.parts() catches (ValueError, FileNotFoundError) round read_block_stacked as "this block has no such part", so with
numpy a corrupt deployed override is now read as absent, silently; without numpy (or before) it is loud.

Hermetic: a temp game root (an explicit existing dir is trusted by find_game_path, so nothing resolves to the real
install) holding one truncated Terrain override. Run from the worktree's ff9mapkit/:
    py ../studies/overworld-editor/perf/review_kernels_truncated.py
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _P
_KIT = _P(__file__).resolve().parents[3] / "ff9mapkit"
_sys.path.insert(0, str(_KIT))
import ff9mapkit as _fk
assert _P(_fk.__file__).resolve().is_relative_to(_KIT), _fk.__file__

import struct
import sys
import tempfile
from pathlib import Path

from ff9mapkit.world import coastnav as CN
from ff9mapkit.world import mesh as M


def build(game: Path):
    p = game / "MOD" / M.override_relpath(1, 5, 5, "0_1", "Terrain")
    p.parent.mkdir(parents=True)
    out = bytearray(M.MAGIC) + struct.pack("<iiii", M.VERSION, 3, 3, 4)       # flags 4: tangents declared
    out += struct.pack("<9f", 0, 0, 0, 1, 0, 0, 0, 0, -1)                     # positions only: truncated
    p.write_bytes(bytes(out))
    (game / "StreamingAssets").mkdir()                                       # a root with no bundles
    return p


def run(label):
    with tempfile.TemporaryDirectory() as td:
        game = Path(td)
        p = build(game)
        try:
            M.read_ff9mesh(p)
            print(label, "read_ff9mesh: read")
        except Exception as e:                     # noqa: BLE001
            print(label, "read_ff9mesh raises", type(e).__name__, "-", e)
        try:
            parts = CN._Loader("MOD", 1, game=str(game)).parts(5, 5)
            print(label, "coastnav parts(5,5) ->", [n for n, _bm, _g in parts], "(the corrupt Terrain read as absent)")
        except Exception as e:                     # noqa: BLE001
            print(label, "coastnav parts(5,5) raises", type(e).__name__, "-", e)


def main():
    run("[numpy lane]   ")
    saved = sys.modules.get("numpy")
    sys.modules["numpy"] = None                     # `import numpy` inside read_ff9mesh now raises ImportError
    try:
        run("[struct lane]  ")
    finally:
        sys.modules["numpy"] = saved


if __name__ == "__main__":
    main()
