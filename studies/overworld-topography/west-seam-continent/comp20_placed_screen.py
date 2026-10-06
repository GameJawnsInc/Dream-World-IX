"""COMP20-BENCH.md's C2 -- the sector-map instrument re-aimed at comp20 on the bench (read-only).

The sector map (sector_map.py) is donor- and placement-parameterised by module globals: point them at
comp20 and the carve's printed centre, point FF9MK_WM at the bench, and it calibrates the placement by
matching carried rock verts to the bench mesh, then reads every rim station against the pre-massif lawn.

    FF9MK_WM=<bench>/FF9_Data/WorldMap py -X utf8 comp20_placed_screen.py CX,CZ [--png OUT]
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sector_map as SM                                    # noqa: E402

cx, cz = (float(v) for v in sys.argv[1].split(","))
SM.DONOR = [(12, 16), (12, 17)]                             # --donor 12,16-17 (cli _parse_block_rect order)
SM.HOME_RING = [(bx, by) for bx in range(11, 14) for by in range(15, 19)]
SM.CENTRE = (cx, cz)
SM.FAILED_BOX = (0.0, 0.0, 0.0, 0.0)                       # no verdict box: every station scores as PASSED
sys.argv = [sys.argv[0], "--json", str(HERE / "comp20_placed_screen.json")] + sys.argv[2:]
SM.main()
