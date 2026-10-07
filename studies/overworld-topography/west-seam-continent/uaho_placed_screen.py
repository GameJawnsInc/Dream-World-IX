"""R5-UAHO-BENCH.md's U2 -- the sector-map instrument re-aimed at Uaho on the bench (read-only).

Like comp20_placed_screen.py, plus one thing Uaho needs: the carve builds Uaho's blob WITH its alcove floor
(alcove="auto" for donor (0,0) -> interior.UAHO_ALCOVE), so the instrument must too, or its rim would not be
the carved one. The sector map calls interior._mountain_blob(alcove_box=None); this wraps that call.

    FF9MK_WM=<bench>/FF9_Data/WorldMap py -X utf8 uaho_placed_screen.py CX,CZ [--png OUT]
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sector_map as SM                                    # noqa: E402

_real_blob = SM.IN._mountain_blob


def _blob_with_alcove(blocks, **kw):
    kw["alcove_box"] = SM.IN.UAHO_ALCOVE
    return _real_blob(blocks, **kw)


SM.IN._mountain_blob = _blob_with_alcove
cx, cz = (float(v) for v in sys.argv[1].split(","))
SM.DONOR = [(0, 0)]
SM.HOME_RING = [(bx % 24, by % 20) for bx in (-1, 0, 1) for by in (-1, 0, 1)]
SM.CENTRE = (cx, cz)
SM.FAILED_BOX = (0.0, 0.0, 0.0, 0.0)                       # no verdict box: every station scores as PASSED
sys.argv = [sys.argv[0], "--json", str(HERE / "uaho_placed_screen.json")] + sys.argv[2:]
SM.main()
